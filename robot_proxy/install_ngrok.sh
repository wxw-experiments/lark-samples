curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
  && echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list \
  && sudo apt update \
  && sudo apt install ngrok


export YOUR_AUTHTOKEN=3GkjVThB9cJ731KiqJueXSIMsFo_2s6m4APcAhjxSK3vxTV5G
ngrok config add-authtoken $YOUR_AUTHTOKEN

ngrok http --url=jiffy-hypnosis-handshake.ngrok-free.dev 3000