from __future__ import annotations

from datetime import datetime

from flask import Blueprint, request

from app.extensions import db
from app.models import Robot, User, UserRobotLink
from app.utils.auth import get_current_user, roles_required
from app.utils.response import api_error, api_success

bp = Blueprint("robots", __name__, url_prefix="/api/robots")


def _allowed_robot_ids(user):
    if user.role == "admin":
        return None
    rows = UserRobotLink.query.filter_by(user_id=user.id).all()
    return [r.robot_id for r in rows]


@bp.get("/map")
@roles_required("admin", "user")
def list_robots_for_map():
    rows = Robot.query.order_by(Robot.created_at.desc()).all()
    robot_ids = [r.id for r in rows]

    link_map: dict[int, UserRobotLink] = {}
    user_map: dict[int, User] = {}
    if robot_ids:
        links = UserRobotLink.query.filter(UserRobotLink.robot_id.in_(robot_ids)).all()
        for link in links:
            link_map[link.robot_id] = link
        user_ids = [x.user_id for x in links]
        if user_ids:
            users = User.query.filter(User.id.in_(user_ids)).all()
            user_map = {u.id: u for u in users}

    result = []
    for row in rows:
        item = row.to_dict()
        link = link_map.get(row.id)
        bound_user = user_map.get(link.user_id) if link else None
        item["bound_user_id"] = bound_user.id if bound_user else None
        item["bound_username"] = bound_user.username if bound_user else None
        item["bound_user_display_name"] = bound_user.display_name if bound_user else None
        result.append(item)

    return api_success(result)


@bp.get("")
@roles_required("admin", "user")
def list_robots():
    user = get_current_user()
    assert user is not None

    q = Robot.query
    allowed = _allowed_robot_ids(user)
    if allowed is not None:
        if not allowed:
            return api_success([])
        q = q.filter(Robot.id.in_(allowed))

    keyword = str(request.args.get("keyword", "")).strip()
    if keyword:
        q = q.filter((Robot.robot_code.contains(keyword)) | (Robot.name.contains(keyword)))

    status = str(request.args.get("status", "")).strip()
    if status:
        q = q.filter(Robot.status == status)

    rows = q.order_by(Robot.created_at.desc()).all()
    robot_ids = [r.id for r in rows]

    link_map: dict[int, UserRobotLink] = {}
    user_map: dict[int, User] = {}
    if robot_ids:
        links = UserRobotLink.query.filter(UserRobotLink.robot_id.in_(robot_ids)).all()
        for link in links:
            link_map[link.robot_id] = link
        user_ids = [x.user_id for x in links]
        if user_ids:
            users = User.query.filter(User.id.in_(user_ids)).all()
            user_map = {u.id: u for u in users}

    result = []
    for row in rows:
        item = row.to_dict()
        link = link_map.get(row.id)
        bound_user = user_map.get(link.user_id) if link else None
        item["bound_user_id"] = bound_user.id if bound_user else None
        item["bound_username"] = bound_user.username if bound_user else None
        item["bound_user_display_name"] = bound_user.display_name if bound_user else None
        result.append(item)

    return api_success(result)


@bp.post("")
@roles_required("admin")
def create_robot():
    data = request.get_json(silent=True) or {}
    robot_code = str(data.get("robot_code", "")).strip()
    name = str(data.get("name", "")).strip()

    if not robot_code or not name:
        return api_error("机器人编号和名称不能为空", code=4001)
    if Robot.query.filter_by(robot_code=robot_code).first() is not None:
        return api_error("机器人编号已存在", code=4002)

    row = Robot(
        robot_code=robot_code,
        name=name,
        capacity_total=float(data.get("capacity_total", 100.0)),
        capacity_used=float(data.get("capacity_used", 0.0)),
        status=str(data.get("status", "available")),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        is_online=bool(data.get("is_online", False)),
        rtsp_url=str(data.get("rtsp_url", "")).strip() or None,
    )
    db.session.add(row)
    db.session.commit()
    return api_success(row.to_dict(), message="创建成功")


@bp.put("/<int:robot_id>")
@roles_required("admin")
def update_robot(robot_id: int):
    row = Robot.query.get(robot_id)
    if row is None:
        return api_error("机器人不存在", code=4041, http_status=404)

    data = request.get_json(silent=True) or {}
    for key in ["name", "status"]:
        if key in data:
            setattr(row, key, str(data.get(key)))
    if "rtsp_url" in data:
        row.rtsp_url = str(data.get("rtsp_url", "")).strip() or None
    for key in ["capacity_total", "capacity_used", "latitude", "longitude"]:
        if key in data and data.get(key) is not None:
            setattr(row, key, float(data.get(key)))
    if "is_online" in data:
        row.is_online = bool(data.get("is_online"))

    db.session.commit()
    return api_success(row.to_dict(), message="更新成功")


@bp.delete("/<int:robot_id>")
@roles_required("admin")
def delete_robot(robot_id: int):
    row = Robot.query.get(robot_id)
    if row is None:
        return api_error("机器人不存在", code=4041, http_status=404)
    db.session.delete(row)
    db.session.commit()
    return api_success(message="删除成功")


@bp.post("/<int:robot_id>/bind")
@roles_required("admin")
def bind_robot(robot_id: int):
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 0))
    if user_id <= 0:
        return api_error("user_id 不能为空", code=4001)

    user = User.query.get(user_id)
    robot = Robot.query.get(robot_id)
    if user is None or robot is None:
        return api_error("用户或机器人不存在", code=4041, http_status=404)

    existed_user_link = UserRobotLink.query.filter_by(user_id=user_id).first()
    if existed_user_link and existed_user_link.robot_id != robot_id:
        return api_error("该用户已绑定其他机器人，一个用户只能绑定一台机器人", code=4003)

    existed_robot_link = UserRobotLink.query.filter_by(robot_id=robot_id).first()
    if existed_robot_link and existed_robot_link.user_id != user_id:
        return api_error("该机器人已绑定其他用户", code=4004)

    if UserRobotLink.query.filter_by(user_id=user_id, robot_id=robot_id).first() is not None:
        return api_error("绑定关系已存在", code=4002)

    link = UserRobotLink(user_id=user_id, robot_id=robot_id, alias=str(data.get("alias", "")).strip() or None)
    db.session.add(link)
    db.session.commit()
    return api_success(link.to_dict(), message="绑定成功")


@bp.delete("/<int:robot_id>/bind/<int:user_id>")
@roles_required("admin")
def unbind_robot(robot_id: int, user_id: int):
    link = UserRobotLink.query.filter_by(user_id=user_id, robot_id=robot_id).first()
    if link is None:
        return api_error("绑定关系不存在", code=4041, http_status=404)
    db.session.delete(link)
    db.session.commit()
    return api_success(message="解绑成功")


@bp.post("/<int:robot_id>/heartbeat")
@roles_required("admin", "user")
def robot_heartbeat(robot_id: int):
    user = get_current_user()
    assert user is not None

    robot = Robot.query.get(robot_id)
    if robot is None:
        return api_error("机器人不存在", code=4041, http_status=404)

    if user.role != "admin":
        link = UserRobotLink.query.filter_by(user_id=user.id, robot_id=robot_id).first()
        if link is None:
            return api_error("无权访问该机器人", code=4031, http_status=403)

    data = request.get_json(silent=True) or {}
    robot.is_online = bool(data.get("is_online", True))
    robot.last_heartbeat = datetime.utcnow()
    if "capacity_used" in data:
        robot.capacity_used = float(data.get("capacity_used"))
    if "status" in data:
        robot.status = str(data.get("status"))
    if "latitude" in data:
        robot.latitude = float(data.get("latitude"))
    if "longitude" in data:
        robot.longitude = float(data.get("longitude"))

    db.session.commit()
    return api_success(robot.to_dict(), message="心跳已更新")
