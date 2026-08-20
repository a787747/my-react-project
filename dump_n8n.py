import requests
import json
import os
import re

N8N_URL = os.environ.get("N8N_URL", "").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
OUTPUT_DIR = os.environ.get("N8N_OUTPUT_DIR", "./n8n_workflows")

if not N8N_URL or not API_KEY:
    raise SystemExit(
        "Set N8N_URL and N8N_API_KEY environment variables before running this script."
    )

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

headers = {
    "X-N8N-API-KEY": API_KEY
}

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_all_workflows():
    workflows = []
    cursor = None
    
    print(f"Подключаемся к {N8N_URL} для получения списка...")
    
    while True:
        url = f"{N8N_URL}/api/v1/workflows?limit=100"
        if cursor:
            url += f"&cursor={cursor}"
            
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Ошибка API: {response.status_code}")
                break
                
            data = response.json()
            workflows.extend(data['data'])
            
            cursor = data.get('nextCursor')
            if not cursor:
                break
        except Exception as e:
            print(f"Ошибка соединения: {e}")
            return []
            
    return workflows

# 1. Получаем все
all_workflows = get_all_workflows()

# 2. ФИЛЬТРУЕМ (Берем только те, что начинаются на 'API')
filtered_workflows = [
    wf for wf in all_workflows 
    if (
        wf['name'].strip().startswith("API:")
        and not wf.get('isArchived', False)
    )
]

print(f"Всего воркфлоу: {len(all_workflows)}")
print(f"Из них начинаются на 'API': {len(filtered_workflows)}")

if not filtered_workflows:
    print("Ничего не найдено. Проверьте, точно ли названия начинаются с заглавных 'API'.")
    raise SystemExit(0)

# 3. Скачиваем отфильтрованные
print("\nНачинаю скачивание...")
for i, wf in enumerate(filtered_workflows, 1):
    wf_id = wf['id']
    wf_name = wf['name']
    
    full_resp = requests.get(
        f"{N8N_URL}/api/v1/workflows/{wf_id}",
        headers=headers,
        timeout=30,
    )
    
    if full_resp.status_code == 200:
        wf_data = full_resp.json()
        safe_name = clean_filename(wf_name)
        filename = f"{OUTPUT_DIR}/{safe_name}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(wf_data, f, indent=2, ensure_ascii=False)
            
        print(f"[{i}/{len(filtered_workflows)}] Сохранен: {wf_name}")
    else:
        print(f"[{i}/{len(filtered_workflows)}] Ошибка: {wf_name}")

print(f"\nГотово! Файлы лежат в папке {OUTPUT_DIR}")