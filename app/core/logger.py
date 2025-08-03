import logging
import sys

# Tạo logger
logger = logging.getLogger('price_tracker')
logger.setLevel(logging.INFO)

# Tạo handler để ghi log ra console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Định dạng log
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Thêm handler vào logger
logger.addHandler(console_handler)