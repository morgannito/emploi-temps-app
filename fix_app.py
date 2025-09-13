# Corriger le fichier app_new.py

with open("app_new.py", "r") as f:
    lines = f.readlines()

# Supprimer la ligne dupliquée (ligne 764)
if "# Si aucune semaine n'est spécifiée, on prend la première de la liste générée" in lines[764]:
    lines.pop(764)
    print("Ligne dupliquée supprimée")

with open("app_new.py", "w") as f:
    f.writelines(lines)

print("Correction appliquée!")
