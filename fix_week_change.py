# Corriger la fonction changeWeekPlanningV2
with open('templates/planning_v2.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacer l'ancienne fonction par une version simplifiée
old_function = '''    function changeWeekPlanningV2(selectedOption) {
        var select = document.getElementById('week-select');
        var selectedText = select.options[select.selectedIndex].text;
        var weekMatch = selectedText.match(/Semaine \d+ [AB]/);
        if (weekMatch) {
            var weekName = encodeURIComponent(weekMatch[0]);
            window.location.href = '/planning_v2_fast/' + weekName;
        }
    }'''

new_function = '''    function changeWeekPlanningV2(selectedUrl) {
        window.location.href = selectedUrl;
    }'''

content = content.replace(old_function, new_function)

with open('templates/planning_v2.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fonction changeWeekPlanningV2 corrigée')
