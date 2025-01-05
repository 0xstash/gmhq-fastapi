import os
import sys
import boto3
from griptape.chunkers import TextChunker
from griptape.drivers import (
    LocalVectorStoreDriver,
    OpenAiChatPromptDriver,
    OpenAiEmbeddingDriver,
    AstraDbVectorStoreDriver,
    PostgresVectorStoreDriver,
    AmazonOpenSearchVectorStoreDriver,
)
from griptape.engines.rag import RagEngine
from griptape.engines.rag.modules import (
    PromptResponseRagModule,
    VectorStoreRetrievalRagModule,
)
from griptape.engines.rag.stages import ResponseRagStage, RetrievalRagStage
from griptape.loaders import PdfLoader
from griptape.structures import Agent
from griptape.tools import RagTool
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()
namespace = "document"


def test_vector_stores(query):
    console = Console()
    table = Table(title="Vector Store Query Results")
    table.add_column("Vector Store", style="cyan", justify="right")
    table.add_column("Response", style="magenta")
    table.add_column("Status", style="green")

    artifacts = PdfLoader().load("test/data/mert_visa.pdf")
    chunks = TextChunker().chunk(artifacts)

    vector_stores = {
        "Local": LocalVectorStoreDriver(
            embedding_driver=OpenAiEmbeddingDriver(),
            persist_file="vector_store_local.json",
        ),
        "AstraDB": AstraDbVectorStoreDriver(
            embedding_driver=OpenAiEmbeddingDriver(),
            token=os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
            api_endpoint=os.getenv("ASTRA_DB_API_ENDPOINT"),
            collection_name=os.getenv("ASTRA_DB_COLLECTION_NAME"),
            astra_db_namespace=os.getenv("ASTRA_DB_NAMESPACE"),
        ),
        "PgVector": PostgresVectorStoreDriver(
            embedding_driver=OpenAiEmbeddingDriver(),
            connection_string=os.getenv("POSTGRES_CONNECTION_STRING"),
            table_name="embeddings",
            schema_name="public",
        ),
        "AmazonOpenSearch": AmazonOpenSearchVectorStoreDriver(
            host=os.environ["AMAZON_OPENSEARCH_HOST"],
            index_name=os.environ["AMAZON_OPENSEARCH_INDEX_NAME"],
            session=boto3.Session(),
            embedding_driver=OpenAiEmbeddingDriver(),
        ),
    }

    for name, vector_store_driver in vector_stores.items():
        try:
            vector_store_driver.upsert_text_artifacts({namespace: chunks})

            engine = RagEngine(
                retrieval_stage=RetrievalRagStage(
                    retrieval_modules=[
                        VectorStoreRetrievalRagModule(
                            vector_store_driver=vector_store_driver,
                            query_params={"namespace": namespace, "top_n": 20},
                        )
                    ]
                ),
                response_stage=ResponseRagStage(
                    response_modules=[
                        PromptResponseRagModule(
                            prompt_driver=OpenAiChatPromptDriver(model="gpt-4")
                        )
                    ]
                ),
            )

            rag_tool = RagTool(
                description="Contains user uploaded documents. Use this tool to answer any questions that you do not confidently know.",
                rag_engine=engine,
            )
            agent = Agent(tools=[rag_tool])
            response = agent.run(query).output

            table.add_row(name, str(response), "[green]✓ Success[/green]")

        except Exception as e:
            print(f"Debug - {name} error: {str(e)}")
            table.add_row(name, f"Error: {str(e)}", "[red]✗ Failed[/red]")

    console.print(table)


# Test all vector stores with the same query
test_vector_stores("What did Mert do for work?")
