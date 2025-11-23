
"""
LangChain + Neo4j Integration for Banking Transactions
Uses GraphCypherQAChain for natural language to Cypher translation

Requirements:
    pip install langchain langchain-community langchain-neo4j langchain-core
    pip install langchain-openai  # For OpenAI
    pip install langchain-anthropic  # For Anthropic
    pip install openai anthropic
"""

import os
from typing import Optional
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate  # Changed from langchain.prompts


class BankingTransactionQA:
    """Natural language query interface for banking transactions using LangChain"""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "12345678",
        database: str = "neo4j",
        llm_provider: str = "openai",  # "openai" or "anthropic"
        model: str = None,
        api_key: Optional[str] = openai_key,
        temperature: float = 0
    ):
        """
        Initialize the QA system
        
        Args:
            uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
            database: Neo4j database name
            llm_provider: "openai" or "anthropic"
            model: Model name (default: gpt-4 or claude-3-5-sonnet-20241022)
            api_key: API key (if not in environment)
            temperature: LLM temperature (0 = deterministic)
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        
        # Initialize Neo4j Graph
        print("Connecting to Neo4j...")
        self.graph = Neo4jGraph(
            url=uri,
            username=username,
            password=password,
            database=database
        )
        
        # Initialize LLM
        print(f"Initializing {llm_provider} LLM...")
        self.llm = self._initialize_llm(llm_provider, model, api_key, temperature)
        
        # Create custom prompt for banking domain
        self.cypher_prompt = self._create_banking_prompt()
        
        # Initialize QA Chain
        print("Creating QA Chain...")
        self.qa_chain = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            verbose=True,
            allow_dangerous_requests=True,
            cypher_prompt=self.cypher_prompt,
            return_intermediate_steps=True,
            top_k=10
        )
        
        print("✓ Banking Transaction QA system ready!\n")
    
    def _initialize_llm(self, provider: str, model: Optional[str], api_key: Optional[str], temperature: float):
        """Initialize the LLM based on provider"""
        if provider.lower() == "openai":
            from langchain_openai import ChatOpenAI
            
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
            
            model_name = model or "gpt-4o"
            return ChatOpenAI(
                model=model_name,
                temperature=temperature
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Use 'openai' ")
    
    def _create_banking_prompt(self):
        """Create a custom prompt template for banking domain"""
        template = """
You are a Neo4j expert helping users query a banking transaction database.

The database schema is:
- Partner nodes: Represent people or businesses with banking accounts
  Properties: partner_id, partner_name, partner_gender, partner_phone_number, 
  partner_address, industry_gic2_code, partner_class_code, account_iban, 
  account_currency, account_open_date, account_close_date

- TRANSACTED relationships: Direct transactions between partners
  Properties: transaction_id, date, amount, balance_after, debit_credit, 
  currency, transfer_type, is_internal (true=internal, false=external),
  ext_counterparty_country, ext_counterparty_account

Patterns:
- Internal transfer: (Partner A)-[TRANSACTED]->(Partner B) where is_internal=true
- External transaction: (Partner A)-[TRANSACTED]->(Partner A) where is_internal=false
- Current balance: Latest transaction's balance_after property

Important rules:
1. ALWAYS filter self-loops for network analysis: WHERE startNode(t) <> endNode(t)
2. For internal transfers: WHERE t.is_internal = true
3. For external transactions: WHERE t.is_internal = false
4. Current balance: ORDER BY t.date DESC LIMIT 1, return t.balance_after
5. Use partner_name for searches, partner_id for precise matches
6. Dates are stored as strings in format 'YYYY-MM-DD'

Schema:
{schema}

Question: {question}

Generate a Cypher query to answer the question. Only return the Cypher query, nothing else.
"""
        
        return PromptTemplate(
            input_variables=["schema", "question"],
            template=template
        )
        
    def query_cypher(self, cypher: str, params: dict = None):
        """Execute a Cypher query directly"""
        return self.graph.query(cypher, params or {})
    
    def refresh_schema(self):
        """Refresh the graph schema"""
        self.graph.refresh_schema()
        print("✓ Schema refreshed")
    
    def get_schema(self):
        """Get the current graph schema"""
        return self.graph.schema
