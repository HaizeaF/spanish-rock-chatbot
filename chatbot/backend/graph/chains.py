from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_ollama import ChatOllama
from chatbot.backend.graph.prompts import (ANSWER_PROMPT, HALLUCINATION_GRADER_PROMPT, QUESTION_ROUTER_PROMPT, RELEVANCE_GRADER_PROMPT, WEB_RESULTS_GRADER_PROMPT)
from chatbot.backend.config import LLM_MODEL

_llm_json = ChatOllama(model=LLM_MODEL, format="json", temperature=0)
_llm = ChatOllama(model=LLM_MODEL, temperature=0.2)

question_router = (
    PromptTemplate(template=QUESTION_ROUTER_PROMPT, input_variables=["history", "question"])
    | _llm_json
    | JsonOutputParser()
)

relevance_grader = (
    PromptTemplate(template=RELEVANCE_GRADER_PROMPT, input_variables=["history", "question", "documents"])
    | _llm_json
    | JsonOutputParser()
)

answer_chain = (
    PromptTemplate(template=ANSWER_PROMPT, input_variables=["history", "context", "question"])
    | _llm
    | StrOutputParser()
)

web_results_grader = (
    PromptTemplate(template=WEB_RESULTS_GRADER_PROMPT, input_variables=["document"])
    | _llm_json
    | JsonOutputParser()
)

hallucination_grader = (
    PromptTemplate(template=HALLUCINATION_GRADER_PROMPT, input_variables=["documents","generation"])
    | _llm_json
    | JsonOutputParser()
)