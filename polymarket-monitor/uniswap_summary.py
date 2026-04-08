#!/usr/bin/env python3
import json

with open('uniswap_v3_ca_cap_swap.json') as f:
    data = json.load(f)

summary = {
    'title': data['title'],
    'timestamp': data['timestamp'],
    'cap_function': {
        'name': data['cap_function']['name'],
        'description': data['cap_function']['description'],
        'contracts': data['cap_function']['contracts'],
        'features': data['cap_function']['features']
    },
    'swap_function': {
        'name': data['swap_function']['name'],
        'description': data['swap_function']['description'],
        'contracts': data['swap_function']['contracts'],
        'functions': data['swap_function']['functions']
    },
    'implementation': {
        'cap_pools': list(data['implementation']['cap_pool_contracts'].keys()),
        'swap_router': list(data['implementation']['swap_router_contracts'].keys())
    },
    'examples': {
        'cap_pool': data['examples']['cap_pool_example'],
        'swap': data['examples']['swap_example']
    }
}

print(json.dumps(summary, indent=2, ensure_ascii=False))
