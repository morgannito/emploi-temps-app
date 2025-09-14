# MANUAL PRESTASHOP BACK-OFFICE INSPECTION CHECKLIST

## 1. LOGS SYSTÈME

### PHP Error Logs
```bash
# Sur le serveur
tail -f /var/log/plesk-php82-fpm/error.log | grep -i prestashop
grep -i "fatal\|critical\|error" /var/log/plesk-php82-fpm/error.log | tail -50
```

### PrestaShop Logs
```bash
cd /var/www/vhosts/heleneriu.fr/httpdocs/var/logs
ls -la *.log
tail -50 *.log
```

## 2. TESTS SECTIONS BACK-OFFICE

### Dashboard Principal (https://heleneriu.fr/pelo66/)
- [ ] Page se charge sans erreur 500/404
- [ ] Graphiques s'affichent
- [ ] Notifications présentes
- [ ] Métriques temps réel fonctionnent

### Commandes (/index.php?controller=AdminOrders)
- [ ] Liste des commandes s'affiche
- [ ] Filtres fonctionnent
- [ ] Détail commande accessible
- [ ] Statuts modifiables
- [ ] Impression factures OK

### Catalogue (/index.php?controller=AdminProducts)
- [ ] Liste produits se charge
- [ ] Création nouveau produit
- [ ] Modification produit existant
- [ ] Upload d'images fonctionne
- [ ] Catégories navigables

### Clients (/index.php?controller=AdminCustomers)
- [ ] Liste clients complète
- [ ] Recherche fonctionne
- [ ] Fiche client détaillée
- [ ] Historique commandes visible

### Modules (/index.php?controller=AdminModules)
- [ ] Liste modules s'affiche
- [ ] Installation nouveau module
- [ ] Activation/désactivation
- [ ] Configuration modules

## 3. VÉRIFICATIONS BASE DE DONNÉES

```sql
-- Connexion DB
mysql -u heleneridlbouton -p'a70Icc92!' heleneridlbouton

-- Tables principales
SELECT COUNT(*) as products FROM ps_product;
SELECT COUNT(*) as orders FROM ps_orders;
SELECT COUNT(*) as customers FROM ps_customer;

-- Intégrité référentielle
SELECT COUNT(*) as orphaned_order_details
FROM ps_order_detail od
LEFT JOIN ps_orders o ON od.id_order = o.id_order
WHERE o.id_order IS NULL;

-- Tables corrompues
CHECK TABLE ps_product, ps_orders, ps_customer, ps_cart;

-- Index manquants
SHOW INDEX FROM ps_product;
SHOW INDEX FROM ps_orders;
```

## 4. PERFORMANCE CHECKS

### Tailles Répertoires
```bash
cd /var/www/vhosts/heleneriu.fr/httpdocs
du -sh var/cache/
du -sh var/logs/
du -sh img/
du -sh upload/
```

### Cache Status
```bash
ls -la var/cache/smarty/compile/
ls -la var/cache/prod/
```

### Templates Compilés
```bash
find var/cache/smarty/compile/ -name "*.php" | wc -l
```

## 5. SÉCURITÉ

### Permissions Fichiers
```bash
# Vérification permissions critiques
ls -la config/settings.inc.php
ls -ld var/cache/
ls -ld var/logs/
ls -ld img/
ls -ld upload/
```

### Configuration PHP
```bash
php -i | grep -E "(memory_limit|max_execution_time|upload_max_filesize)"
```

### Modules Obsolètes
```bash
ls modules/ | grep -E "(autoupgrade|ps_checkout|ps_facebook)"
```

## 6. ERREURS UX COMMUNES À TESTER

### Navigation
- [ ] Menu latéral fonctionnel
- [ ] Recherche globale
- [ ] Breadcrumbs corrects

### Formulaires
- [ ] Validation côté client
- [ ] Messages d'erreur clairs
- [ ] Sauvegarde sans perte données

### Performance UI
- [ ] Temps de chargement < 3s
- [ ] Pas de timeouts
- [ ] Pagination fonctionnelle

## 7. MAINTENANCE TOOLS

### Outils Système (/index.php?controller=AdminMaintenance)
- [ ] Mode maintenance activable
- [ ] Clear cache fonctionne
- [ ] Regenerate thumbnails
- [ ] Check/repair DB

### SEO & URLs (/index.php?controller=AdminMeta)
- [ ] Friendly URLs actives
- [ ] Meta descriptions
- [ ] Redirections 301/302

## 8. PATTERNS D'ERREURS À RECHERCHER

### Dans les logs PHP:
- `Fatal error`
- `MySQL server has gone away`
- `Memory limit exceeded`
- `Maximum execution time`
- `Call to undefined`
- `Class not found`

### Dans les logs PrestaShop:
- `CRITICAL`
- `ERROR`
- `Database`
- `Template`
- `Hook`
- `Module`

## 9. RAPPORT DE BUG STANDARD

```
PRIORITY: [Critical|High|Medium|Low]
SECTION: [Dashboard|Orders|Products|Customers|etc.]
ERROR: [Description courte]
FILE: [path/to/file.php:line]
REPRODUCTION:
1. Step 1
2. Step 2
3. Error occurs

IMPACT: [User cannot...]
SUGGESTED FIX: [Brief solution]
```

## 10. COMMANDES DE DIAGNOSTIC RAPIDE

```bash
# Quick health check
cd /var/www/vhosts/heleneriu.fr/httpdocs

# Check core files
test -f classes/PrestaShop/PrestaShop/Core/Foundation/Database/Core_Foundation_Database_Database.php && echo "Core OK" || echo "Core MISSING"

# Check config
test -f config/settings.inc.php && echo "Config OK" || echo "Config MISSING"

# Check writable dirs
test -w var/cache && echo "Cache writable" || echo "Cache NOT writable"
test -w var/logs && echo "Logs writable" || echo "Logs NOT writable"

# Check recent errors
tail -20 /var/log/plesk-php82-fpm/error.log | grep -i "$(date '+%d-%b-%Y')"
```