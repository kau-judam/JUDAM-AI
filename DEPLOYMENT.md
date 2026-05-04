# AWS EC2 배포 가이드

주담 AI 서버 AWS EC2 배포 방법

## 사전 준비

### 필요한 것
- AWS 계정
- EC2 인스턴스 (Ubuntu 22.04 LTS 권장)
- 도메인 (선택사항)
- SSL 인증서 (선택사항)

### 권장 사양
- **CPU**: 2 vCPU 이상
- **RAM**: 4GB 이상
- **Storage**: 20GB 이상 (SSD)
- **인스턴스 타입**: t3.medium 또는 t3.large

## 1. EC2 인스턴스 생성

### 1.1 인스턴스 시작

```bash
# AWS Console 접속
# EC2 → 인스턴스 → 인스턴스 시작

# 설정
- AMI: Ubuntu Server 22.04 LTS
- 인스턴스 유형: t3.medium
- 키 페어: 새로 생성 (다운로드 필수)
- 네트워크 설정:
  - 보안 그룹: HTTP(80), HTTPS(443), SSH(22), 사용자 포트(8000)
```

### 1.2 보안 그룹 설정

| 유형 | 프로토콜 | 포트 범위 | 소스 |
|------|----------|-----------|------|
| SSH | TCP | 22 | 내 IP |
| HTTP | TCP | 80 | 0.0.0.0/0 |
| HTTPS | TCP | 443 | 0.0.0.0/0 |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 (또는 Nginx만 열면 불필요) |

## 2. 서버 초기 설정

### 2.1 SSH 접속

```bash
# 키 페어 권한 설정
chmod 400 your-key.pem

# SSH 접속
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

### 2.2 시스템 업데이트

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.3 필수 패키지 설치

```bash
# Python 3.12 설치
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev -y

# PostgreSQL 클라이언트
sudo apt install postgresql-client -y

# Nginx
sudo apt install nginx -y

# Git
sudo apt install git -y

# Supervisor (프로세스 관리)
sudo apt install supervisor -y
```

### 2.4 방화벽 설정

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 3. 프로젝트 배포

### 3.1 코드 복제

```bash
# 프로젝트 디렉토리 생성
sudo mkdir -p /var/www/juddam-ai
sudo chown ubuntu:ubuntu /var/www/juddam-ai

# 코드 복제
cd /var/www/juddam-ai
git clone https://github.com/kau-judam/JUDAM-AI.git .
```

### 3.2 가상환경 설정

```bash
cd /var/www/juddam-ai
python3.12 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 환경변수 설정

```bash
# .env 파일 생성
nano .env
```

```env
# 데이터베이스 (RDS 또는 외부 DB)
DATABASE_URL=postgresql+asyncpg://user:password@your-db-host:5432/juddam

# 외부 API
GEMINI_API_KEY=your_gemini_api_key
LAW_API_KEY=your_law_api_key

# Redis (ElastiCache 또는 외부)
REDIS_URL=redis://your-redis-host:6379

# 서버 설정
HOST=0.0.0.0
PORT=8000
WORKERS=4
```

### 3.4 권한 설정

```bash
# 로그 디렉토리 생성
sudo mkdir -p /var/log/juddam-ai
sudo chown ubuntu:ubuntu /var/log/juddam-ai
```

## 4. 데이터베이스 설정

### 4.1 RDS 생성 (권장)

```bash
# AWS Console → RDS → 데이터베이스 생성

# 설정
- 엔진: PostgreSQL
- 버전: 15.x
- 인스턴스 클래스: db.t3.micro (개발) / db.t3.medium (프로덕션)
- 스토리지: 20GB
- VPC: EC2와 동일한 VPC
- 보안 그룹: EC2 보안 그룹에서 접근 허용
```

### 4.2 데이터베이스 초기화

```bash
# EC2에서 DB 연결 테스트
psql -h your-db-host -U user -d juddam

# 테이블 초기화 (앱 시작 시 자동 생성됨)
# 또는 수동 실행:
python -c "from app.db import db; import asyncio; asyncio.run(db.initialize_tables())"
```

## 5. Nginx 설정

### 5.1 Nginx 설정 파일

```bash
sudo nano /etc/nginx/sites-available/juddam-ai
```

```nginx
upstream juddam_ai {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;  # 또는 EC2 퍼블릭 IP

    client_max_body_size 10M;

    location / {
        proxy_pass http://juddam_ai;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 지필요시
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 정적 파일 캐싱
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 5.2 설정 활성화

```bash
sudo ln -s /etc/nginx/sites-available/juddam-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 6. SSL 인증서 (HTTPS)

### 6.1 Certbot 설치

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 6.2 인증서 발급

```bash
sudo certbot --nginx -d your-domain.com
```

### 6.3 자동 갱신 설정

```bash
sudo certbot renew --dry-run
# 자동 갱신은 cron에 이미 설정됨
```

## 7. 프로세스 관리 (Supervisor)

### 7.1 Supervisor 설정

```bash
sudo nano /etc/supervisor/conf.d/juddam-ai.conf
```

```ini
[program:juddam-ai]
command=/var/www/juddam-ai/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/var/www/juddam-ai
user=ubuntu
autostart=true
autorestart=true
stderr_logfile=/var/log/juddam-ai/err.log
stdout_logfile=/var/log/juddam-ai/out.log
environment=PYTHONPATH="/var/www/juddam-ai"
```

### 7.2 Supervisor 시작

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start juddam-ai
sudo supervisorctl status
```

## 8. 모니터링

### 8.1 로그 확인

```bash
# 앱 로그
tail -f /var/log/juddam-ai/out.log
tail -f /var/log/juddam-ai/err.log

# Nginx 로그
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Supervisor 로그
sudo supervisorctl tail juddam-ai
```

### 8.2 프로세스 관리

```bash
# 서비스 재시작
sudo supervisorctl restart juddam-ai

# 서비스 중지
sudo supervisorctl stop juddam-ai

# 서비스 상태
sudo supervisorctl status juddam-ai
```

## 9. 배포 스크립트

### 9.1 자동 배포 스크립트

```bash
# deploy.sh
#!/bin/bash

cd /var/www/juddam-ai

# Git pull
git pull origin main

# 가상환경 활성화
source venv/bin/activate

# 의존성 업데이트
pip install -r requirements.txt

# 서비스 재시작
sudo supervisorctl restart juddam-ai

echo "배포 완료!"
```

### 9.2 스크립트 실행 권한

```bash
chmod +x deploy.sh
./deploy.sh
```

## 10. CI/CD (선택사항)

### 10.1 GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to EC2

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Deploy to EC2
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.EC2_HOST }}
        username: ubuntu
        key: ${{ secrets.EC2_SSH_KEY }}
        script: |
          cd /var/www/juddam-ai
          git pull origin main
          source venv/bin/activate
          pip install -r requirements.txt
          sudo supervisorctl restart juddam-ai
```

## 11. 비용 최적화

### 11.1 비용 절감 팁

1. **개발 환경**: t3.micro 사용
2. **프로덕션**: t3.medium + 오토스케일링
3. **RDS**: db.t3.micro → 필요시 스케일업
4. **스케줄링**: 사용량이 적은 시간대 인스턴스 중지

### 11.2 예상 비용 (월)

| 서비스 | 사양 | 비용 |
|--------|------|------|
| EC2 | t3.medium (24시간) | 약 $30 |
| RDS | db.t3.micro (24시간) | 약 $15 |
| ElastiCache | cache.t3.micro (24시간) | 약 $20 |
| **합계** | | **약 $65/월** |

## 12. 문제 해결

### 12.1 포트 충돌

```bash
# 포트 사용 확인
sudo netstat -tlnp | grep 8000

# 프로세스 종료
sudo kill -9 <PID>
```

### 12.2 권한 문제

```bash
# 디렉토리 권한
sudo chown -R ubuntu:ubuntu /var/www/juddam-ai

# 로그 권한
sudo chown -R ubuntu:ubuntu /var/log/juddam-ai
```

### 12.3 DB 연결 실패

```bash
# 보안 그룹 확인
# AWS Console → RDS → 보안 그룹 → EC2 IP 허용

# 연결 테스트
psql -h your-db-host -U user -d juddam
```

## 13. 백업

### 13.1 DB 백업

```bash
# 자동 백업 스크립트
#!/bin/bash
BACKUP_DIR="/var/backups/juddam"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

pg_dump -h your-db-host -U user juddam > $BACKUP_DIR/juddam_$DATE.sql

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "juddam_*.sql" -mtime +7 -delete
```

### 13.2 S3 백업

```bash
# AWS CLI 설치
sudo apt install awscli -y

# S3에 백업 업로드
aws s3 cp $BACKUP_DIR/juddam_$DATE.sql s3://juddam-backups/
```

## 14. 보안

### 14.1 SSH 보안

```bash
# root 로그인 비활성화
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# 비밀번호 인증 비활성화
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# SSH 재시작
sudo systemctl restart sshd
```

### 14.2 방화벽

```bash
# 불필요한 포트 닫기
sudo ufw deny 8000  # Nginx만 사용 시
```

## 15. 도메인 설정

### 15.1 Route 53

```bash
# AWS Console → Route 53 → 호스팅 영역 생성

# 레코드 추가
- 유형: A
- 이름: api
- 값: EC2 퍼블릭 IP
```

### 15.2 DNS 확인

```bash
# DNS 전파 확인
nslookup api.your-domain.com
```

## 완료 체크리스트

- [ ] EC2 인스턴스 생성
- [ ] 보안 그룹 설정
- [ ] Python 및 필수 패키지 설치
- [ ] 프로젝트 코드 배포
- [ ] 환경변수 설정
- [ ] RDS 데이터베이스 생성
- [ ] Nginx 설정
- [ ] SSL 인증서 발급
- [ ] Supervisor 설정
- [ ] 서비스 정상 작동 확인
- [ ] 로그 모니터링 설정
- [ ] 백업 스크립트 설정
- [ ] 도메인 연결 (선택사항)
