import os
from dotenv import load_dotenv

load_dotenv()


def get_pinecone_vector_store_driver(index_name):
    from griptape.drivers import OpenAiEmbeddingDriver, PineconeVectorStoreDriver

    vector_store_driver = PineconeVectorStoreDriver(
        embedding_driver=OpenAiEmbeddingDriver(),
        project_name="godmode",
        api_key=os.getenv("PINECONE_API_KEY"),
        index_name=index_name,
        environment="prod",
    )

    return vector_store_driver


def get_people_database_tool():
    from griptape.drivers import OpenAiChatPromptDriver
    from griptape.engines import RagEngine
    from griptape.engines.rag.stages import RetrievalRagStage, ResponseRagStage
    from griptape.engines.rag.modules import (
        VectorStoreRetrievalRagModule,
        PromptResponseRagModule,
    )
    from griptape.tools import DateTimeTool, WebScraperTool, RagTool

    people_vector_store_driver = get_pinecone_vector_store_driver("people")
    engine = RagEngine(
        retrieval_stage=RetrievalRagStage(
            retrieval_modules=[
                VectorStoreRetrievalRagModule(
                    vector_store_driver=people_vector_store_driver,
                    query_params={
                        "count": 20,
                        "namespace": "dev",
                    },
                )
            ]
        ),
        response_stage=ResponseRagStage(
            response_modules=[
                PromptResponseRagModule(
                    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
                )
            ]
        ),
    )
    rag_tool = RagTool(
        description="You are tasked to answer questions about people and companies I know. You have a database of records containing them. ",
        rag_engine=engine,
        off_prompt=False,
    )
    rag_tool.name = "PeopleDatabase"
    return rag_tool
