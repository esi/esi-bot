# ESI-bot

Connects to slack via RTM API, does stuff there. Important stuff.

[![Build
Status](https://travis-ci.org/esi/esi-bot.svg?branch=master)](https://travis-ci.org/esi/esi-bot)
[![Coverage Status](https://coveralls.io/repos/github/esi/esi-bot/badge.svg?branch=master)](https://coveralls.io/github/esi/esi-bot?branch=master)


## Config

All config is done through environment variables. They are:

  * `SLACK_TOKEN`: slack legacy token to auth with
  * `BOT_CHANNELS`: comma separated list of channels to respond in
