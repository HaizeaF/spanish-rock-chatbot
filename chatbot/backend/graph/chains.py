"""LLM chain definitions for the chatbot's agents.
 
Two different local models are used, chosen for the specific demands of each task.
"""

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_ollama import ChatOllama
from chatbot.backend.prompts.prompts import QUESTION_REWRITER_PROMPT, ANSWER_PROMPT, QUESTION_ROUTER_PROMPT, QUERY_KEYWORDS_PROMPT
from chatbot.backend.prompts.grader_prompts import HALLUCINATION_GRADER_PROMPT, WEB_RESULTS_GRADER_PROMPT
from chatbot.backend.config.config import Config

_llm_json = ChatOllama(model=Config.LLM_MODEL, format="json", temperature=0)
_llm_rewriter = ChatOllama(model=Config.WRITER_LLM_MODEL, format="json", temperature=0)
_llm = ChatOllama(model=Config.WRITER_LLM_MODEL, temperature=0)

question_rewriter = (
    PromptTemplate(template=QUESTION_REWRITER_PROMPT, input_variables=["history", "question"])
    | _llm_rewriter
    | JsonOutputParser()
)

question_router = (
    PromptTemplate(template=QUESTION_ROUTER_PROMPT, input_variables=["question"])
    | _llm_json
    | JsonOutputParser()
)

keywords_generator = (
    PromptTemplate(template=QUERY_KEYWORDS_PROMPT, input_variables=["question"])
    | _llm_json
    | JsonOutputParser()
)

answer_chain = (
    PromptTemplate(template=ANSWER_PROMPT, input_variables=["context", "question"])
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