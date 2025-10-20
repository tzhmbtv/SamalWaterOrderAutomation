# 🚀 Production Setup Guide

## Быстрая установка на сервер

### 1. Подключитесь к серверу
```bash
ssh root@92.38.49.171
```

### 2. Установите необходимое ПО
```bash
apt update
apt install -y python3 python3-pip python3-venv git nano
```

### 3. Создайте пользователя для бота
```bash
useradd -m -s /bin/bash samalbot
su - samalbot
```

### 4. Клонируйте проект
```bash
git clone https://github.com/tzhmbtv/SamalWaterOrderAutomation.git
cd SamalWaterOrderAutomation
```

### 5. Настройте окружение
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. Создайте .env файл
```bash
nano .env
```

Содержимое:
```env
TELEGRAM_BOT_TOKEN=ваш_токен
DEFAULT_PRODUCT_ID=224
DEFAULT_QUANTITY=2
LOG_LEVEL=ERROR
```

### 7. Создайте systemd сервис
Вернитесь к root:
```bash
exit
nano /etc/systemd/system/samalbot.service
```

Содержимое:
```ini
[Unit]
Description=Samal Water Telegram Bot
After=network.target

[Service]
Type=simple
User=samalbot
WorkingDirectory=/home/samalbot/SamalWaterOrderAutomation
Environment="PATH=/home/samalbot/SamalWaterOrderAutomation/venv/bin"
ExecStart=/home/samalbot/SamalWaterOrderAutomation/venv/bin/python /home/samalbot/SamalWaterOrderAutomation/bot.py
Restart=always
RestartSec=10

# Минимальное логирование (только ошибки)
StandardOutput=null
StandardError=append:/var/log/samalbot_error.log

[Install]
WantedBy=multi-user.target
```

### 8. Запустите сервис
```bash
touch /var/log/samalbot_error.log
chown samalbot:samalbot /var/log/samalbot_error.log

systemctl daemon-reload
systemctl start samalbot
systemctl enable samalbot
systemctl status samalbot
```

## Управление ботом

```bash
# Проверить статус
systemctl status samalbot

# Перезапустить
systemctl restart samalbot

# Остановить
systemctl stop samalbot

# Посмотреть ошибки (если есть)
tail -f /var/log/samalbot_error.log
```

## Обновление бота

```bash
su - samalbot
cd SamalWaterOrderAutomation
source venv/bin/activate
git pull
exit

systemctl restart samalbot
```

## Логирование

Бот настроен на **минимальное логирование** для экономии места:
- Только критичные ошибки записываются в лог
- Обычные операции не логируются
- Нет избыточного вывода в консоль

Для включения расширенного логирования (для отладки):
```bash
nano /home/samalbot/SamalWaterOrderAutomation/.env
# Измените LOG_LEVEL=ERROR на LOG_LEVEL=INFO
```

Затем перезапустите:
```bash
systemctl restart samalbot
```

**Важно:** После отладки верните обратно `LOG_LEVEL=ERROR`!

