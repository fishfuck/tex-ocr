# Tex-OCR 屏幕公式识别工具

一个跨平台的屏幕公式OCR识别工具，支持多显示器截图和LaTeX公式识别，能够自动将识别结果复制到剪贴板。

## 🌟 功能特性

- **跨平台支持**：Windows、Linux、macOS
- **多显示器支持**：自动检测并支持多显示器配置
- **全局热键**：支持快捷键快速截图
- **智能识别**：自动识别数学公式并转换为LaTeX格式
- **多种格式**：支持行内公式、块级公式等不同LaTeX格式
- **自动复制**：识别结果自动复制到系统剪贴板

## 📋 系统要求

- Python 3.7+
- 支持的操作系统：Windows 10+、Linux、macOS 10.14+
- 网络连接（用于API调用）

## 🚀 安装步骤

### 1. 克隆项目
```bash
git clone https://github.com/fishfuck/tex-ocr.git
cd tex-ocr
```

### 2. 安装依赖
```bash
# 使用pip安装
pip install -r requirements.txt

# 或使用pip3（macOS/Linux）
pip3 install -r requirements.txt
```

### 3. 配置API密钥
请前往 [SimpleTeX API文档](https://simpletex.cn/api_doc) 注册并获取API服务，我们使用APP鉴权方式。

创建 `.ini` 配置文件：
```ini
[Simpletex]
APP_ID = your_app_id_here
APP_SECRET = your_app_secret_here
```

**注意**：请将 `your_app_id_here` 和 `your_app_secret_here` 替换为你的真实API凭据。

## 🎯 使用方法

### 启动程序
```bash
python simplatex/gui.py
# 或
python3 simplatex/gui.py
```

### 界面操作
1. 启动程序后，会显示主窗口
2. **选择接口**：选择使用"轻量接口"或"标准接口"
   - 轻量接口：`https://server.simpletex.cn/api/latex_ocr_turbo`（默认）
   - 标准接口：`https://server.simpletex.cn/api/latex_ocr`
3. 点击"开始截图"按钮开始截图
4. 使用鼠标拖拽选择要识别的区域
5. 释放鼠标完成截图，程序自动识别并复制结果

### 截图操作说明
- **选择区域**：左键拖拽选择截图区域
- **取消截图**：右键点击或按ESC键取消当前截图
- **操作提示**：鼠标悬停在截图窗口上会显示操作提示

### 全局热键
程序支持以下全局热键组合：

#### Windows
- `Ctrl + Shift + Win`：识别为行内公式 `$...$`
- `Ctrl + Shift + Alt`：识别为块级公式 `$$\n...\n$$`
- `Ctrl + Win + Alt`：识别为块级公式 `$$...$$`

#### macOS
- `Ctrl + Shift + Cmd`：识别为行内公式 `$...$`
- `Ctrl + Shift + Alt`：识别为块级公式 `$$\n...\n$$`
- `Ctrl + Alt + Cmd`：识别为块级公式 `$$...$$`

#### Linux
- `Ctrl + Shift + Super`：识别为行内公式 `$...$`
- `Ctrl + Shift + Alt`：识别为块级公式 `$$\n...\n$$`
- `Ctrl + Alt + Super`：识别为块级公式 `$$...$$`

## 🔧 配置说明

### 配置文件格式
`.ini` 文件必须包含以下内容：
```ini
[Simpletex]
APP_ID = 你的APP_ID
APP_SECRET = 你的APP_SECRET
```

### 配置文件位置
- 配置文件 `.ini` 应放在项目根目录下
- 与 `simplatex/` 文件夹同级

## 📱 多显示器支持

程序自动检测多显示器配置：
- 支持不同分辨率的显示器
- 自动计算显示器边界和相对位置
- 截图时自动选择对应的显示器

## 🛠️ 故障排除

### 常见问题

#### 1. 配置文件错误
**症状**：程序启动时显示配置错误
**解决**：检查 `.ini` 文件格式和API凭据是否正确

#### 2. 全局热键不工作
**症状**：快捷键无法触发截图
**解决**：
- Windows：确保以管理员权限运行
- Linux：检查是否有权限问题
- macOS：检查系统偏好设置中的辅助功能权限

#### 3. 截图失败
**症状**：截图后显示"截图失败"
**解决**：
- 检查显示器配置
- 确保有足够的屏幕访问权限
- 重启程序

#### 4. 依赖安装失败
**症状**：`pip install` 失败
**解决**：
- 更新pip：`pip install --upgrade pip`
- 使用虚拟环境
- 检查Python版本兼容性

### 调试信息
程序运行时会在控制台输出详细的调试信息，包括：
- 显示器检测结果
- 截图区域坐标
- API调用状态
- 错误详情

## 🔒 安全注意事项

- **不要**将包含真实API密钥的 `.ini` 文件提交到版本控制系统
- `.ini` 文件已添加到 `.gitignore` 中
- 定期更换API密钥
- 不要在公共环境中暴露API凭据

## 📁 项目结构

```
tex-ocr/
├── simplatex/
│   ├── gui.py              # 主界面和截图逻辑
│   ├── DisplayScaling.py   # 跨平台显示器信息获取
│   ├── SimpletexApi.py     # API接口封装
│   └── favicon.ico         # 程序图标
├── requirements.txt         # Python依赖列表
├── .gitignore              # Git忽略文件
└── README.md               # 项目说明文档
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

### 开发环境设置
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 🙏 致谢

- [SimpleTeX](https://simpletex.cn) - 提供OCR API服务
- [mss](https://github.com/BoboTiG/python-mss) - 跨平台截图库
- [pynput](https://github.com/moses-palmer/pynput) - 跨平台输入监听库

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至：[riyu020423@gmail.com]

---

**注意**：使用本工具前，请确保遵守相关API服务的使用条款和限制。 