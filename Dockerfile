# esi-bot

FROM python:3.6
MAINTAINER Adam Talsma <adam@talsma.ca>

ADD requirements.txt /bot/
RUN pip install -qr /bot/requirements.txt

ENV SLACK_TOKEN="" \
    BOT_CHANNELS="esi"

ADD . /bot/
WORKDIR /bot/

RUN pip install -q . \
    && groupadd -r esibot \
    && useradd -r -g esibot -d / -s /usr/sbin/nologin -c "esibot" esibot \
    && rm -rf /bot

WORKDIR /

USER esibot
CMD esi-bot
