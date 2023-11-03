Discord message scraper BY: Muhammad Zain Raza

1. extracting token:
   - open and login web discord
   - go to any text channel
   - open developer tools
   - click on the message input box of the channel and type any letter
   - observe the api call with the name 'typing' on the network tab and click on it
   - go to headers of the request and extraction the token which is by the key 'Authorization' in headers
2. put token in config.json
3. enable developer tools on your discord web by going to settings > advance > enable developer tools
4. now right click on any channel and click the 'copy channel id' to extract channel id
5. put channel id in config.json
6. put start date and end date in config.json in this format (yyyy-mm-dd)
