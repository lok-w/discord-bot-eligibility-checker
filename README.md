# discord-bot-eligibility-checker

This checkbot is for the ETH NFT project to setup a chatbot in their discord server.

The chatbot provides three main functions:
- submit wallet address
- check eligibility of the wallet address 
- apply Google Sheet API as a database to store and retrieve members data

One thing to note that in order to write async functions, this chatbot used library "gspread_asyncio" instead of regualar "gspread".
