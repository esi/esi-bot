# ESI-bot

Connects to slack via IRC gateway, does stuff there. Important stuff.


## Config

All config is done through environment variables. They are:

  * `IRC_NAME`: the name of the bot. default: "ccp_snowedin"
  * `IRC_REALNAME`: the IRC "realname" of the bot. default: "ccp_snowedin"
  * `IRC_SSL`: set this to 1 or true for ssl. do not set otherwise
  * `IRC_NETWORK`: DNS name or IP of the IRC network
  * `IRC_CHANNELS`: space separated list of channels to connect to
  * `IRC_PASSWORD`: a password, or a file path to a file containing the password on a single line and nothing else
  * `SLACK_WEBHOOK_URL`: a url for incoming webhooks
