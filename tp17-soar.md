# TP 17 : Réponse automatisée aux incidents (Auto-Remédiation)

**Module :** 5 – NetSecDevOps et Sécurité Automatisée · **Durée indicative :** 2 h

Ce TP réutilise exactement la VM OPNsense du TP 7. Le collecteur SOAR est un script Python lancé sur le poste hôte ; aucune VM supplémentaire n'est nécessaire.

## Objectifs

- Recevoir une alerte, décider selon sa sévérité et agir sur OPNsense.
- Bloquer temporairement une IP compromise par l'API REST.
- Éviter le blocage d'adresses de confiance et garder une trace horodatée des décisions.

## Prérequis et configuration

- OPNsense du TP 7 démarré et accessible depuis le poste hôte.
- Python 3 et les dépendances :

  ```bash
  pip install fastapi uvicorn requests pydantic python-dotenv
  ```

- Les identifiants API du TP 7 dans `.env` (fichier ignoré par Git) :

  ```dotenv
  OPNSENSE_HOST=https://192.168.50.1
  API_KEY=votre_cle_api
  API_SECRET=votre_secret_api
  VERIFY_SSL=false
  SOAR_ALIAS=soar_blocklist
  SOAR_BLOCK_SECONDS=3600
  SOAR_WHITELIST=127.0.0.1,::1,192.168.50.1
  ```

  Les identifiants `OPNSENSE_KEY` et `OPNSENSE_SECRET` sont aussi acceptés. `VERIFY_SSL=false` est prévu uniquement pour le certificat autosigné du labo. Remplacez la liste blanche par les adresses réelles du poste hôte, des administrateurs et des équipements à protéger.

## Préparation côté OPNsense

1. Dans **Firewall → Aliases**, créez `soar_blocklist`, de type **Host(s)**, vide.
2. Dans **Firewall → Rules → LAN** (ou l'interface du scénario), créez en première position une règle **Block** dont la source est `soar_blocklist`, puis appliquez.
3. Vérifiez la présence de l'alias avec les identifiants définis dans `.env` :

   ```bash
   curl -k -u "$API_KEY:$API_SECRET" \
     https://192.168.50.1/api/firewall/alias/getAliasUUID/soar_blocklist
   ```

L'utilisateur API doit avoir les permissions permettant de gérer les alias. Le script utilise les routes OPNsense `firewall/alias_util/add/{alias}` et `firewall/alias_util/delete/{alias}` pour ajouter puis retirer une adresse. L'API alias_util documente ces appels pour les alias Host, Network et External. [Guide officiel des alias OPNsense](https://docs.opnsense.org/manual/aliases.html)

## Lancement

Dans le dossier du projet, avec l'environnement Python du TP 7 activé :

```bash
python soar_listener.py
```

Le webhook écoute sur `http://localhost:5000/webhook/alert`, la documentation interactive est sur `http://localhost:5000/docs`, et l'état de santé sur `http://localhost:5000/health`. Pour recevoir un webhook depuis un autre poste, utilisez l'adresse IP du poste hôte et autorisez le port 5000 dans son pare-feu.

## Scénarios de vérification

### Alerte élevée : blocage temporaire

```bash
curl -X POST http://localhost:5000/webhook/alert \
  -H "Content-Type: application/json" \
  -d '{"source_ip":"203.0.113.50","severity":"high","type":"bruteforce_ssh"}'
```

La réponse attendue indique `status: blocked`. Vérifiez l'adresse dans **Firewall → Diagnostics → Aliases** ou dans la table de l'alias. Après `SOAR_BLOCK_SECONDS` (une heure par défaut), le collecteur appelle l'API pour retirer l'adresse.

### Alerte faible : aucune action

```bash
curl -X POST http://localhost:5000/webhook/alert \
  -H "Content-Type: application/json" \
  -d '{"source_ip":"203.0.113.51","severity":"low","type":"scan"}'
```

La réponse attendue indique `status: ignored`; cette IP ne doit pas être ajoutée à l'alias.

### Adresse de la liste blanche

Remplacez l'adresse d'exemple ci-dessous par une adresse inscrite dans `SOAR_WHITELIST`, puis redémarrez le collecteur si `.env` vient d'être modifié :

```bash
curl -X POST http://localhost:5000/webhook/alert \
  -H "Content-Type: application/json" \
  -d '{"source_ip":"192.168.50.1","severity":"critical","type":"test_whitelist"}'
```

La réponse attendue indique `status: whitelisted`; l'adresse ne doit pas être ajoutée à l'alias, même si l'alerte est critique.

## Journalisation et rendu

Le fichier `soar_actions.log` est créé au lancement et trace l'heure, l'alerte reçue, la décision (IGNORE, BLOCK, WHITELIST, BLOCK_FAILED ou UNBLOCK), l'IP et la durée prévue. Vérifiez-le après chaque scénario.

Rendu attendu : `soar_listener.py`, les dépendances dans l'environnement du TP, `soar_actions.log` avec les scénarios exercés et une capture de l'alias peuplé dans OPNsense. Ne versionnez pas `.env` ni les secrets API.

**Limite pédagogique :** le minuteur est en mémoire. Si le collecteur s'arrête ou redémarre avant l'expiration, la suppression automatique déjà programmée ne sera pas restaurée. En production, utiliser un ordonnanceur persistant et une authentification du webhook.
