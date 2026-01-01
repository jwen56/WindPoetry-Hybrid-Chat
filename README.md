# 🍃 WindPoetry-Hybrid-Chat

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Hybrid-purple)](https://github.com/RVC-Boss/GPT-SoVITS)
[![TTS](https://img.shields.io/badge/Audio-GPT--SoVITS-orange)](https://github.com/RVC-Boss/GPT-SoVITS)
[![Inspiration](https://img.shields.io/badge/Inspiration-SillyTavern-darkred)](https://github.com/SillyTavern/SillyTavern)
[![License](https://img.shields.io/badge/License-MIT-green)]()

**[English](#english) | [简体中文](#chinese)**

---

<a name="english"></a>
## 📖 English

### Introduction

**WindPoetry-Hybrid-Chat** is a Python-based hybrid dialogue orchestration terminal. It is engineered to bridge the gap between high-intelligence cloud LLMs and low-latency local neural speech synthesis.

Unlike standard API wrappers, this project implements a **non-blocking asynchronous architecture**. It orchestrates complex context management, advanced regex post-processing pipelines, and real-time audio inference via a local **GPT-SoVITS** engine, creating an immersive, voice-enabled roleplay experience.

> *"Weaving code into poetry, and text into voice."*

### 💡 Motivation & Acknowledgements

This project was heavily inspired by [SillyTavern](https://github.com/SillyTavern/SillyTavern).

The journey began with a specific need: I wanted to eliminate robotic speech in local TTS by utilizing **Auxiliary Reference Audio** with GPT-SoVITS—a feature I initially found lacking in existing integrations. Driven by this, I built WindPoetry from scratch using **Vibe Coding**, referencing some of SillyTavern's excellent design concepts along the way.

Although I later discovered that SillyTavern is powerful enough to support these features via extensions, WindPoetry stands as a unique outcome of this journey. It is a streamlined, lightweight alternative, tailored for those who desire a concise, highly customizable experience without the complexity of a massive framework.

### ✨ Key Features

* **⚡ Hybrid Cloud-Local Architecture:**
    * **Brain (Cloud):** Integrates OpenAI-compatible LLM APIs (e.g., Gemini, GPT-4) for high-quality narrative generation.
    * **Voice (Local):** Connects to a local GPT-SoVITS inference engine via `GPTSoVITSTTSEngine.py` for ultra-low latency, custom-trained character voices.
* **🧵 Multi-threaded & Non-blocking:**
    * Implements `threading` to handle API communication and audio synthesis separately, ensuring the Tkinter GUI remains responsive during long-text generation.
* **🔤 Advanced Regex Pipeline:**
    * Features a custom parser (`_parse_js_regex`) that converts JavaScript-style regex (e.g., `/pattern/flags`) into Python `re` objects.
    * Automatically sanitizes AI outputs (removing CoT, HTML tags) before TTS processing to ensure clean audio output.
* **🧩 Dynamic Context Orchestration:**
    * **Preset Modules:** A JSON-based system to inject custom instructions (e.g., World Info, Style Guides, Scenario Setups) dynamically into the system prompt.
    * **Persona Management:** Separates System Prompts, Character settings, and User personas.
* **🔀 Interactive Branching:**
    * Parses custom `<branches>` tags from LLM responses to render interactive choice buttons on the UI, gamifying the dialogue experience.
* **💾 State Persistence:**
    * Auto-saves session states (API keys, active modules, TTS configs) to `session_state.json`.

### 🛠️ Architecture Overview

The project consists of two core components:

1.  **`WindPoetry.py` (The Conductor):**
    * Manages the GUI lifecycle (Tkinter).
    * Constructs the final system prompt by combining Personas + Preset Modules.
    * Handles the Regex cleaning pipeline and branch parsing.
    * Manages session state serialization.

2.  **`GPTSoVITSTTSEngine.py` (The Voice):**
    * Encapsulates the GPT-SoVITS API communication.
    * Handles Primary Reference Audio and Auxiliary Reference Audio injection, and text language detection.
    * Manages temporary audio file caching (`tts_cache/`).

### 🚀 Quick Start

1.  **Prerequisites**
    * Python 3.10+
    * A running [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) API instance (default: `http://127.0.0.1:9880`).
    * An LLM API Key (OpenAI-compatible).

2.  **Installation**
    ```bash
    git clone [https://github.com/YourUsername/WindPoetry-Hybrid-Chat.git](https://github.com/YourUsername/WindPoetry-Hybrid-Chat.git)
    cd WindPoetry-Hybrid-Chat
    
    # Install required library for API requests
    pip install requests
    ```

3.  **Run**
    ```bash
    python WindPoetry.py
    ```

### 📸 Interface Gallery

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <img width="1351" height="931" alt="image" src="https://github.com/user-attachments/assets/6b61c356-f176-4a05-bb8d-13a83f166ad6" />
      <br>
      <h3>1. Immersive Chat Terminal</h3>
      <p align="left">
        The main hub featuring real-time dialogue streaming. Highlight includes the <b>Interactive Branch Buttons</b> (bottom) dynamically parsed from AI responses.
      </p>
    </td>
    <td width="50%" align="center" valign="top">
      <img width="636" height="278" alt="image" src="https://github.com/user-attachments/assets/cadffb43-5774-472b-ad48-70c8741dc23f" />
      <br>
      <h3>2. API & Model Configuration</h3>
      <p align="left">
        Universal API panel compatible with OpenAI standards. Supports dynamic model fetching and seamless provider switching.
      </p>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <img width="637" height="852" alt="image" src="https://github.com/user-attachments/assets/db7c226c-1c30-4859-a215-d8a5954c6542" />
      <br>
      <h3>3. Persona Orchestration</h3>
      <p align="left">
        Dedicated profile management for AI Characters and User Personas. Configures names, biographies, and first messages for the system prompt.
      </p>
    </td>
    <td width="50%" align="center" valign="top">
      <img width="637" height="255" alt="image" src="https://github.com/user-attachments/assets/d5c2d6d8-aaec-4f10-a653-c46017c9a94b" />
      <br>
      <h3>4. Preset Modules</h3>
      <p align="left">
        A modular prompt injection system. Users can toggle JSON-based instruction sets (World Info, Style Guides) to dynamically alter the context.
      </p>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <img width="632" height="215" alt="image" src="https://github.com/user-attachments/assets/ed46564d-0cc0-4771-9aa2-9a706c9cfe46" />
      <br>
      <h3>5. Advanced Regex Pipeline</h3>
      <p align="left">
        Visual editor for the post-processing engine. Converts JS-style regex to Python objects to sanitize outputs (removing CoT/HTML) before TTS.
      </p>
    </td>
    <td width="50%" align="center" valign="top">
      <img width="626" height="825" alt="image" src="https://github.com/user-attachments/assets/92bc875b-3b24-47dc-ba40-9efc00e25f12" />
      <br>
      <h3>6. Local TTS Integration</h3>
      <p align="left">
        Configuration for the local GPT-SoVITS inference engine. Manages primary reference audio and auxiliary reference audio injection, and cross-language settings.
      </p>
    </td>
  </tr>
</table>

---

<a name="chinese"></a>
## 🎋 简体中文

### 项目简介

**WindPoetry-Hybrid-Chat**（风之诗·混合对话终端）是一个基于 Python 开发的混合架构对话系统。它的核心目标是解决云端大模型的“高智商”与本地语音合成的“低延迟”之间的协同问题。

本项目不仅仅是一个 API 客户端，它采用了**非阻塞的异步架构**，将复杂的上下文编排、高级正则后处理流水线以及本地 **GPT-SoVITS** 推理引擎无缝结合，构建了一个沉浸式的、支持实时语音交互的 AI 角色扮演终端。

> *“以代码编织诗篇，将文字化作风声。”*

### 💡 开发初衷与致谢

本项目深受 [SillyTavern (酒馆)](https://github.com/SillyTavern/SillyTavern) 的启发。

最初开发这个项目的动力源于我对本地 GPT-SoVITS 语音合成效果的执念——当时我认为现有的工具难以便捷地支持“副参考音频” (Auxiliary Reference Audio)，导致合成语气略显僵硬，人机感太重。于是，我决定从零开始，通过 **Vibe Coding** ，参考酒馆的部分设计理念，手搓了这个能够完美连接本地 GPT-SoVITS 的客户端。

虽然项目完成后我才发现原版酒馆其实早已具备强大的扩展能力来实现类似功能，但 WindPoetry 依然是我学习历程的一个独特里程碑。现在的它，是一个去繁就简、完全满足我个人定制化需求的轻量级“风之诗”。

### ✨ 核心亮点

* **⚡ 云端+本地 混合架构：**
    * **大脑 (云端):** 集成兼容 OpenAI 格式的 LLM API（如 Gemini, GPT-4）处理复杂的叙事逻辑。
    * **嗓音 (本地):** 通过 `GPTSoVITSTTSEngine.py` 封装接口，调用本地部署的 GPT-SoVITS 模型，实现克隆音色的实时合成。
* **🧵 多线程与非阻塞设计：**
    * 使用 `threading` 库分离 API 请求与音频合成任务，确保在生成长文本或合成语音时，Tkinter 图形界面依然保持流畅响应。
* **🔤 高级正则流水线：**
    * 实现了自定义解析算法 (`_parse_js_regex`)，能够将 JavaScript 风格的正则（`/pattern/flags`）自动转换为 Python `re` 对象。
    * 包含自动清洗机制，在 TTS 朗读前移除 AI 输出中的思维链 (CoT) 和 HTML 标签，确保语音干净流畅。
* **🧩 动态上下文编排：**
    * **预设模块:** 基于 JSON 的动态指令系统，支持热插拔“世界观设定”、“文风指南”或“场景剧本”。
    * **角色管理:** 独立的 System Prompt、角色设定与用户人设配置。
* **🔀 分支叙事系统：**
    * 自动解析 LLM 回复中的 `<branches>` 标签，在 UI 上动态生成交互式选项按钮，点击即可推进剧情，实现 AVG 游戏般的体验。
* **💾 状态持久化：**
    * 自动保存当前工作区的所有配置（API Key、激活的预设模块、正则规则）至本地文件，实现无缝断点续传。

### 🛠️ 架构概览

本项目包含两个核心组件：

1.  **`WindPoetry.py` (指挥官):**
    * 管理 Tkinter GUI 生命周期。
    * 负责 Prompt 的组装与拼接 (Persona + Preset Modules)。
    * 执行正则清洗流水线与剧情分支解析。
    * 负责会话状态的序列化与存储。

2.  **`GPTSoVITSTTSEngine.py` (发声单元):**
    * 封装 GPT-SoVITS API 通信逻辑。
    * 处理主参考音频和副参考音频的注入与语言检测。
    * 管理音频文件的临时缓存 (`tts_cache/`)。

### 🚀 快速开始

1.  **环境要求**
    * Python 3.10 或更高版本。
    * 本地已启动的 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) API 服务（默认端口 9880）。
    * 任意支持 OpenAI 格式的 LLM API Key。

2.  **安装步骤**
    ```bash
    git clone [https://github.com/YourUsername/WindPoetry-Hybrid-Chat.git](https://github.com/YourUsername/WindPoetry-Hybrid-Chat.git)
    cd WindPoetry-Hybrid-Chat
    
    # 安装必要的请求库
    pip install requests
    ```

3.  **运行**
    ```bash
    python WindPoetry.py
    ```

### 📸 界面展示

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <img width="1351" height="931" alt="image" src="https://github.com/user-attachments/assets/6b61c356-f176-4a05-bb8d-13a83f166ad6" />
      <br>
      <h3>1. 沉浸式对话终端</h3>
      <p align="left">
        支持实时流式对话的主交互界面。亮点包括底部根据 AI 回复动态解析生成的 <b>交互式分支按钮</b>，提供 AVG 游戏般的剧情推进体验。
      </p>
    </td>
    <td width="50%" align="center" valign="top">
      <img width="636" height="278" alt="image" src="https://github.com/user-attachments/assets/cadffb43-5774-472b-ad48-70c8741dc23f" />
      <br>
      <h3>2. API 与模型配置</h3>
      <p align="left">
        兼容 OpenAI 标准的通用 API 面板。支持动态获取模型列表，并可在不同云端服务商之间无缝切换。
      </p>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <img width="637" height="852" alt="image" src="https://github.com/user-attachments/assets/60c43f64-229e-454c-af9b-5fb75da2e53b" />
      <br>
      <h3>3. 角色编排中心</h3>
      <p align="left">
        专用于 AI 角色和用户人设的配置管理。可配置名称、背景故事及首条消息，用于构建核心系统提示词 (System Prompt)。
      </p>
    </td>
    <td width="50%" align="center" valign="top">
      <img width="637" height="255" alt="image" src="https://github.com/user-attachments/assets/f3afaf91-21c3-45ca-a467-d2f334b65dd8" />
      <br>
      <h3>4. 预设模块管理</h3>
      <p align="left">
        模块化的 Prompt 注入系统。用户可以开关基于 JSON 的指令集（如世界观设定、文风指南），动态地改变叙事上下文。
      </p>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <img width="632" height="215" alt="image" src="https://github.com/user-attachments/assets/11e20bc7-67a0-4774-8e97-5592d23d2567" />
      <br>
      <h3>5. 高级正则流水线</h3>
      <p align="left">
        后处理引擎的可视化编辑器。负责将 JS 风格正则转换为 Python 对象，在语音合成前清洗输出（移除思维链/HTML标签）。
      </p>
    </td>
    <td width="50%" align="center" valign="top">
      <img width="626" height="825" alt="image" src="https://github.com/user-attachments/assets/473f34de-78c5-4524-a2dd-9ffa79d7edf2" />
      <br>
      <h3>6. 本地 TTS 集成</h3>
      <p align="left">
        本地 GPT-SoVITS 推理引擎的配置界面。管理主参考音频和副参考音频的注入以及跨语言合成设置，实现超低延迟的拟真语音交互。
      </p>
    </td>
  </tr>
</table>

---
*Created with ❤️ by Jiejie Wen*
