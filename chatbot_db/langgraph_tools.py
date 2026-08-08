from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import requests

class ChatTools:

    search_tool = DuckDuckGoSearchRun()

    @tool
    def currency_exchange(base: str, target: str, value: str):
        """
        This tool help to return currency exchange between 2 pair, 
        example: USD and EUR are 2 currency pair, it helps to identify 1 USD = ? EUR
        """
        BASE_URL = 'https://api.exchangerate.host/convert?access_key='
        API_KEY = '01c9ffc9cccf7e2337c506cb62e01c3a'
        url = f"{BASE_URL}{API_KEY}&from={base}&to={target}&amount={value}"
        print('URL-> ', url)
        response = requests.get(url=url)
        return response.content

