FROM python:3.10-slim

# 1. Cài đặt các dependencies cần thiết cho Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 2. Tạo thư mục làm việc
WORKDIR /code

# 3. Copy file requirements.txt trước để tận dụng cache
COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. Cài đặt Playwright và trình duyệt
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps

# 5. Copy phần code còn lại
COPY . .

# 6. Chạy app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]