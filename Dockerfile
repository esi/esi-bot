# esi-bot

FROM python:3
MAINTAINER Adam Talsma <se-adam.talsma@ccpgames.com>

ADD requirements.txt /bot/
RUN pip install -qU virtualenv \
&& virtualenv /venv \
&& /venv/bin/pip install -qUr /bot/requirements.txt

ENV IRC_CHANNELS="#esi" \
    IRC_NETWORK="tweetfleet.irc.slack.com" \
    IRC_SSL="" \
    IRC_NAME="esibot" \
    IRC_REALNAME="esibot" \
    IRC_PASSWORD="" \
    SLACK_WEBHOOK=""

ADD bot.py /bot/

RUN groupadd -r esibot \
    && useradd -r -g esibot -d /venv -s /usr/sbin/nologin -c "esibot" esibot \
    && chown -R esibot:esibot /venv /bot

USER esibot

WORKDIR /bot/
CMD /venv/bin/python bot.py
