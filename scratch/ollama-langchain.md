Ollama

Installation

# install package

pip install -U langchain-ollama

Setup
First, follow these instructions to set up and run a local Ollama instance:

    Download and install Ollama onto the available supported platforms (including Windows Subsystem for Linux aka WSL, macOS, and Linux)
        macOS users can install via Homebrew with brew install ollama and start with brew services start ollama
    Fetch available LLM model via ollama pull <name-of-model>
        View a list of available models via the model library
        e.g., ollama pull llama3
    This will download the default tagged version of the model. Typically, the default points to the latest, smallest sized-parameter model.

    On Mac, the models will be download to ~/.ollama/models On Linux (or WSL), the models will be stored at /usr/share/ollama/.ollama/models

    Specify the exact version of the model of interest as such ollama pull vicuna:13b-v1.5-16k-q4_0 (View the various tags for the Vicuna model in this instance)
    To view all pulled models, use ollama list
    To chat directly with a model from the command line, use ollama run <name-of-model>
    View the Ollama documentation for more commands. You can run ollama help in the terminal to see available commands.

Usage
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM

template = """Question: {question}

Answer: Let's think step by step."""

prompt = ChatPromptTemplate.from_template(template)

model = OllamaLLM(model="llama3.1")

chain = prompt | model

chain.invoke({"question": "What is LangChain?"})
