# GitHub Actions CI/CD - .env 설정 가이드

## 방법1: GitHub Secrets 사용 (권장)

### 1. GitHub Secrets 설정
GitHub 리포지토리 → Settings → Secrets and variables → Actions → New repository secret

다음 시크릿을 추가하세요:
```
GEMINI_API_KEY=발급받은_Gemini_API_키
LAW_API_KEY=국가법령정보센터_API_키
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/juddam
REDIS_URL=redis://localhost:6379
```

### 2. EC2 서버에서 .env 파일 생성 스크립트

EC2 서버의 `deploy.sh` 또는 CI/CD 스크립트에 추가:

```bash
#!/bin/bash

# EC2 서버 배포 스크립트

# .env 파일 생성
cat > /home/ubuntu/juddam-ai/.env << EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
LAW_API_KEY=${LAW_API_KEY}
DATABASE_URL=${DATABASE_URL}
REDIS_URL=${REDIS_URL}
LOG_LEVEL=INFO
PORT=8000
EOF

# 권한 설정
chmod 600 /home/ubuntu/juddam-ai/.env

# 서버 재시작
cd /home/ubuntu/juddam-ai
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
pkill -f uvicorn || true
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### 3. GitHub Actions 워크플로우 예시

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to EC2

on:
  push:
    branches: [ master ]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Deploy to EC2
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USERNAME }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /home/ubuntu/juddam-ai
            git pull origin master
            source venv/bin/activate
            pip install -r requirements.txt

            # .env 파일 생성
            cat > .env << EOF
            GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }}
            LAW_API_KEY=${{ secrets.LAW_API_KEY }}
            DATABASE_URL=${{ secrets.DATABASE_URL }}
            REDIS_URL=${{ secrets.REDIS_URL }}
            LOG_LEVEL=INFO
            PORT=8000
            EOF

            chmod 600 .env

            # 서버 재시작
            pkill -f uvicorn || true
            nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

## 방법2: EC2 서버에서 직접 .env 설정

EC2 서버에 SSH 접속 후:

```bash
# .env 파일 생성
cd /home/ubuntu/juddam-ai
nano .env

# 다음 내용 추가
GEMINI_API_KEY=발급받은_Gemini_API_키
LAW_API_KEY=국가법령정보센터_API_키
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/juddam
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
PORT=8000

# 권한 설정
chmod 600 .env

# 서버 재시작
pkill -f uvicorn
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

## EC2 서버에서 현재 상태 확인

```bash
# .env 파일 확인
cat /home/ubuntu/juddam-ai/.env

# 서버 로그 확인
tail -f /home/ubuntu/juddam-ai/server.log

# 헬스체크
curl http://localhost:8000/health
```

## 필요한 GitHub Secrets 목록

| Secret 이름 | 설명 | 예시 |
|------------|------|------|
| EC2_HOST | EC2 서버 IP | 13.125.xxx.xxx |
| EC2_USERNAME | EC2 사용자명 | ubuntu |
| EC2_SSH_KEY | SSH 개인키 | -----BEGIN RSA PRIVATE KEY----- |
| GEMINI_API_KEY | Gemini API 키 | AIza... |
| LAW_API_KEY | 법령정보센터 API 키 | ... |
| DATABASE_URL | DB 연결 URL | postgresql+asyncpg://... |
| REDIS_URL | Redis 연결 URL | redis://... |
