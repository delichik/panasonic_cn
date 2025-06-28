# Panasonic CN Home Assistant Integration

这是一个用于 Home Assistant 的中国大陆松下智能APP集成。

> [!IMPORTANT]
> **这个仓库还处于开发中，无法完成大部分功能** 

## 支持的设备

目前只支持以下设备：

- NR-JS30AX1-W (Fridge-11)

## 安装方法

### 方法一：通过 HACS 安装（推荐）

1. 确保您已经安装了 [HACS](https://hacs.xyz/)
2. 在 HACS 中添加自定义存储库：
   - 点击 HACS 侧边栏
   - 点击右上角的三个点
   - 选择"自定义存储库"
   - 在 URL 中填入：`https://github.com/OWNER/panasonic_cn`
   - 类别选择：`Integration`
   - 点击"添加"
3. 在 HACS 的集成页面中搜索 "Panasonic CN"
4. 点击"下载"进行安装
5. 重启 Home Assistant
6. 在 Home Assistant 的集成页面中添加 "Panasonic CN" 集成

### 方法二：手动安装

1. 下载此仓库
2. 将 `custom_components/panasonic_cn` 文件夹复制到您的 Home Assistant 配置目录中
3. 重启 Home Assistant
4. 在 Home Assistant 的集成页面中添加 "Panasonic CN" 集成

## 配置

在添加集成时，您需要提供以下信息：

- 用户名：您的松下智能APP手机号
- 密码：您的松下智能APP密码

## 许可证

MIT License
