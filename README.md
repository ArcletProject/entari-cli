<div align="center">

# Entari CLI

_✨ Entari 命令行工具 ✨_

</div>

<p align="center">
  <a href="https://raw.githubusercontent.com/ArcletProject/entari-cli/main/LICENSE">
    <img src="https://img.shields.io/github/license/ArcletProject/entari-cli" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/entari-cli">
    <img src="https://img.shields.io/pypi/v/entari-cli" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.9+-blue" alt="python">
</p>

<p align="center">
  <a href="https://arclet.top/tutorial/entari">Entari 文档</a>
</p>

## 功能

- 初始化 Entari 环境
- 启动 Entari
- 生成配置文件
- 管理插件
  - 创建新的 Entari 插件 (项目型/应用型)
- 支持 CLI 插件

## 安装

使用 pipx 安装

```shell
pipx install entari-cli
```

使用 Docker 运行

```shell
docker pull ghcr.io/arcletproject/entari-cli:latest
```

Docker 镜像可以选择以下版本：

- `latest`, `latest-slim`：最新的稳定版本
- `latest-${python版本}`, `latest-${python版本}-slim`：指定 Python 版本的最新稳定版本
- `${cli版本}`, `${cli版本}-slim`：指定 CLI 版本的最新稳定版本
- `${cli版本}-${python版本}`, `${cli版本}-${python版本}-slim`：指定 CLI 和 Python 版本的最新稳定版本

## 命令行使用

```shell
entari --help
```

> **Warning**
>
> 如果找不到 `entari` 命令，请尝试 `pipx ensurepath` 来添加路径到环境变量

- `entari add`            添加一个 Entari 插件到配置文件中
- `entari config`         配置文件操作
- `entari gen_main`       生成一个 Entari 主程序文件
- `entari init`           新建一个虚拟环境并安装 Entari
- `entari new`            新建一个 Entari 插件
- `entari remove`         从配置文件中移除一个 Entari 插件
- `entari run`            运行 Entari

## Docker 镜像使用

```shell
docker run --rm -it -v ./:/workspaces ghcr.io/arcletproject/entari-cli:latest --help
```

挂载当前目录到容器的 `/workspaces` 目录，然后在容器中运行 `entari` 命令。
