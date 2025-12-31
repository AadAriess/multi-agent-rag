ai-service
├── alembic.ini
├── app
│   ├── api
│   │   └── v1
│   │       └── routers
│   │           ├── admin
│   │           │   ├── env_config.py
│   │           │   └── system.py
│   │           ├── ai_detector
│   │           │   └── detector.py
│   │           ├── index.py
│   │           └── lms
│   │               ├── chat.py
│   │               ├── doc.py
│   │               └── quiz.py
│   ├── core
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   └── types
│   │       ├── chat.py
│   │       ├── document.py
│   │       ├── __init__.py
│   │       ├── quiz_output.py
│   │       ├── quiz.py
│   │       ├── system.py
│   │       └── workflow
│   │           ├── event_agent.py
│   │           └── __init__.py
│   ├── database
│   │   ├── __init__.py
│   │   ├── milvus_config.py
│   │   └── mysql_config.py
│   ├── llms
│   │   ├── agents
│   │   │   ├── chat_agent.py
│   │   │   ├── document_agent.py
│   │   │   ├── __init__.py
│   │   │   ├── quiz_agent.py
│   │   │   ├── quiz_generator_agent.py
│   │   │   └── tools
│   │   │       ├── context_tool.py
│   │   │       ├── __init__.py
│   │   │       ├── mcp_tool.py
│   │   │       ├── retrieve_tool.py
│   │   │       └── web_search_tool.py
│   │   ├── ai_detector
│   │   │   └── models
│   │   ├── config_builder.py
│   │   ├── core
│   │   │   ├── ai_detector_load.py
│   │   │   ├── __init__.py
│   │   │   ├── mcp
│   │   │   │   ├── __init__.py
│   │   │   │   └── mcp_client.py
│   │   │   ├── prompt_system.py
│   │   │   └── types
│   │   │       ├── detector_input.py
│   │   │       └── __init__.py
│   │   ├── __init__.py
│   │   ├── llm_facade.py
│   │   ├── local
│   │   │   ├── __init__.py
│   │   │   └── model_local.py
│   │   ├── model_handler.py
│   │   ├── openai_endpoint.py
│   │   ├── openai_handler.py
│   │   └── openai_utils.py
│   ├── main.py
│   ├── models
│   │   ├── database_schema.py
│   │   └── __init__.py
│   ├── services
│   │   ├── chat_service.py
│   │   ├── document_service.py
│   │   ├── __init__.py
│   │   └── quiz_service.py
│   └── utils
│       ├── desklib_model.py
│       ├── file_handler.py
│       ├── __init__.py
│       ├── lmschat_api.py
│       ├── send_notification.py
│       └── text_utils.py
├── mcp.json
├── migrations
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions
│       └── 1eb3715d4c91_initial_db.py
├── pyproject.toml
├── README.md
├── run.py
├── static
│   ├── css
│   │   └── styles.css
│   └── js
│       └── dashboard.js
├── templates
│   ├── dashboard copy.html
│   ├── dashboard.html
│   └── index.html
├── tests
│   ├── api
│   │   └── v1
│   │       ├── test_similarity_search.py
│   │       └── test_system.py
│   ├── conftest.py
│   └── __init__.py
└── uv.lock
