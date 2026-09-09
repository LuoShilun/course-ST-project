lines = []
with open('e:/MyProjectWorkSpace/underwater_project/web_system/frontend/src/views/admin/RAGConfigView.vue', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<el-button' in line and 'testConnection' in line:
        lines[i] = '            <el-button type=\"primary\" @click=\"testConnection\" :loading=\"testing\"><el-icon><Refresh /></el-icon> 测试通道连通</el-button>\n'

with open('e:/MyProjectWorkSpace/underwater_project/web_system/frontend/src/views/admin/RAGConfigView.vue', 'w', encoding='utf-8') as f:
    f.writelines(lines)
