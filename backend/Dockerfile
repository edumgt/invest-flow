FROM node:20-alpine
WORKDIR /app

# postgresql-client: DB 연결용
# python3 + pip + 이미지 처리 라이브러리: classify.py 실행용
RUN apk add --no-cache \
    postgresql-client \
    python3 \
    py3-pip \
    py3-pillow \
    py3-numpy \
    wget \
  && pip3 install --no-cache-dir requests --break-system-packages

COPY package.json ./
RUN npm install
COPY . .

EXPOSE 3000
CMD ["node", "src/server.js"]
