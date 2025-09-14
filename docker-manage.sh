#!/bin/bash

# Скрипт управления Email to Telegram Bot через Docker Compose
# Использование: ./docker-manage.sh [команда]

set -e  # Остановить выполнение при любой ошибке

# Цвета для красивого вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для красивого вывода
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверяем что Docker и Docker Compose установлены
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен! Установите Docker сначала."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен! Установите Docker Compose сначала."
        exit 1
    fi
}

# Проверяем что .env файл существует
check_env_file() {
    if [ ! -f ".env" ]; then
        print_error ".env файл не найден!"
        if [ -f ".env.example" ]; then
            print_warning "Создайте .env файл на основе .env.example"
            print_status "cp .env.example .env"
        fi
        exit 1
    fi
}

# Функция для показа статуса
show_status() {
    print_status "Проверяем статус сервисов..."
    docker-compose ps
    echo
    print_status "Использование ресурсов:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Функция для показа логов
show_logs() {
    local service=${1:-email-bot}
    local lines=${2:-100}
    
    print_status "Показываем последние $lines строк логов для $service..."
    docker-compose logs --tail=$lines -f $service
}

# Функция для входа в контейнер
enter_container() {
    local service=${1:-email-bot}
    print_status "Входим в контейнер $service..."
    docker-compose exec $service bash
}

# Основная функция
main() {
    local command=${1:-help}
    
    case $command in
        "start"|"up")
            check_dependencies
            check_env_file
            print_status "Запускаем Email to Telegram Bot..."
            docker-compose up -d
            print_success "Бот запущен в фоновом режиме!"
            echo
            show_status
            ;;
            
        "stop"|"down")
            print_status "Останавливаем бота..."
            docker-compose down
            print_success "Бот остановлен!"
            ;;
            
        "restart")
            print_status "Перезапускаем бота..."
            docker-compose down
            docker-compose up -d
            print_success "Бот перезапущен!"
            ;;
            
        "build")
            check_dependencies
            check_env_file
            print_status "Пересобираем образ..."
            docker-compose build --no-cache
            print_success "Образ пересобран!"
            ;;
            
        "rebuild")
            print_status "Пересобираем и перезапускаем..."
            docker-compose down
            docker-compose build --no-cache
            docker-compose up -d
            print_success "Готово!"
            ;;
            
        "status")
            show_status
            ;;
            
        "logs")
            show_logs $2 $3
            ;;
            
        "shell"|"bash")
            enter_container $2
            ;;
            
        "clean")
            print_warning "Это удалит все неиспользуемые образы и контейнеры!"
            read -p "Продолжить? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_status "Очищаем Docker..."
                docker system prune -f
                print_success "Очистка завершена!"
            fi
            ;;
            
        "update")
            print_status "Обновляем приложение..."
            git pull
            docker-compose down
            docker-compose build --no-cache
            docker-compose up -d
            print_success "Обновление завершено!"
            ;;
            
        "backup")
            local backup_name="email-bot-backup-$(date +%Y%m%d_%H%M%S)"
            print_status "Создаем резервную копию логов..."
            mkdir -p backups
            cp -r logs backups/$backup_name
            print_success "Резервная копия создана: backups/$backup_name"
            ;;
            
        "help"|*)
            echo -e "${BLUE}Email to Telegram Bot - Docker Management Script${NC}"
            echo
            echo "Использование: $0 [команда]"
            echo
            echo "Доступные команды:"
            echo "  start, up       - Запустить бота в фоновом режиме"
            echo "  stop, down      - Остановить бота"
            echo "  restart         - Перезапустить бота"
            echo "  build           - Пересобрать образ"
            echo "  rebuild         - Пересобрать образ и перезапустить"
            echo "  status          - Показать статус сервисов"
            echo "  logs [service]  - Показать логи (по умолчанию email-bot)"
            echo "  shell [service] - Войти в контейнер"
            echo "  clean           - Очистить неиспользуемые Docker ресурсы"
            echo "  update          - Обновить из git и перезапустить"
            echo "  backup          - Создать резервную копию логов"
            echo "  help            - Показать эту справку"
            echo
            echo "Примеры:"
            echo "  $0 start        # Запустить бота"
            echo "  $0 logs         # Показать логи"
            echo "  $0 logs email-bot 50  # Показать последние 50 строк"
            echo "  $0 shell        # Войти в контейнер бота"
            ;;
    esac
}

# Запускаем основную функцию с переданными аргументами
main "$@"