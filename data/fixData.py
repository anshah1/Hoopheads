import json

with open('data.json', 'r') as file:
    data = json.load(file)

# Create new dictionary with modified keys
sorted_data = {}
for key, value in sorted(data.items()):
    new_key = key.replace('.', '')
    sorted_data[new_key] = value

with open('data.json', 'w') as file:
    json.dump(sorted_data, file, indent=4)