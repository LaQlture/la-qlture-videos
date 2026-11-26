# Production quotidienne — la.qlture (TikTok)

Ce fichier est le mode d'emploi suivi chaque jour par la tâche programmée.
Objectif : fabriquer la vidéo **du jour** et la programmer sur TikTok via Buffer pour **12 h 00 (midi, heure de Paris)**.

## 1. Quel type de vidéo aujourd'hui ?

Alternance stricte, ancrée sur le 26/11/2026 (= histoire) :
- nombre de jours écoulés depuis le 2026-11-26 **pair** → `histoire`
- **impair** → `quiz`

(26/11 histoire, 27/11 quiz, 28/11 histoire, …)

Si `contenu/<date>_<type>.json` **et** `videos/<date>_<type>.mp4` existent déjà, vérifier dans Buffer
(`list_posts` sur la chaîne TikTok) qu'un post est déjà programmé pour aujourd'hui : si oui, ne rien refaire.

## 2. Écrire le contenu

Lire d'abord `historique.md` : **ne jamais réutiliser** un sujet d'histoire ni une question de quiz déjà listés.
Chaque fait, date, chiffre et bonne réponse doit être **vérifié par une recherche web** (sources fiables) avant d'être écrit.
En cas de doute sur un fait : le retirer ou le remplacer.

### Quiz → `contenu/<date>_quiz.json`
```json
{
 "type": "quiz", "date": "AAAA-MM-JJ", "demain": "histoire",
 "questions": [
  {"level": "FACILE", "q": "Quelle planète est surnommée la planète rouge ?",
   "opts": ["Vénus", "Mars", "Jupiter"], "ans": 1, "tts_ans": "Mars !"},
  {"level": "DIFFICILE", "q": "…", "opts": ["…","…","…"], "ans": 2, "tts_ans": "…", "fact": "Anecdote courte (≤ 32 caractères)"}
 ],
 "legende": "Tu fais combien sur 10 ? 🧠 Dis ton score en commentaire 👇 #quiz #culturegenerale #quizz #apprendresurtiktok #culture #testtesconnaissances #fyp"
}
```
Règles :
- exactement **10 questions** : 3 `FACILE`, 3 `MOYEN`, 2 `DIFFICILE`, 2 `EXPERT`, dans cet ordre ;
- 3 choix, **une seule** bonne réponse indiscutable ; `ans` = 0 (A), 1 (B) ou 2 (C), à varier ;
- question ≤ 70 caractères, chaque choix ≤ 18 caractères ;
- `tts_ans` = ce que la voix dit après « Réponse X : » (écrire les symboles en lettres : « a, u » pour Au) ;
- `fact` facultatif (≤ 32 caractères), surtout pour les questions DIFFICILE/EXPERT ;
- thèmes variés (géographie, sciences, histoire, art, animaux, sport, langue française…).

### Histoire → `contenu/<date>_histoire.json`
```json
{
 "type": "histoire", "date": "AAAA-MM-JJ", "demain": "quiz",
 "titre": "Titre accrocheur (≤ 45 caractères)",
 "segments": [
  {"texte": "Tu savais que … ?", "carte": "Accroche courte"},
  {"texte": "Phrase lue par la voix et affichée en sous-titres.", "carte": "1889"},
  {"texte": "Texte affiché avec « guillemets » et 6 000 km.", "tts": "Texte lu sans guillemets, six mille kilomètres.", "carte": "6 000 km"}
 ],
 "legende": "Phrase d'accroche + question au spectateur + 6-8 hashtags (#culturegenerale #histoire #lesavaistu #apprendresurtiktok #fyp …)"
}
```
Règles :
- un seul sujet, raconté comme une histoire avec une chute surprenante ; ton simple, phrases courtes ;
- **12 à 15 segments**, 1 à 2 phrases chacun, **200 à 240 mots** au total (vidéo ≈ 70-80 s) ;
- le 1er segment est une question d'accroche (« Tu savais que… ? ») et sa `carte` résume le choc ;
- `carte` ≤ 24 caractères (mot-clé, date, chiffre) ;
- `tts` seulement si la lecture doit différer du texte affiché : chiffres avec espaces (« six mille »),
  « 1er » → « premier », sigles, guillemets ;
- pas de personne vivante dans une situation négative, pas de sujet politique clivant, pas de drame récent.

## 3. Fabriquer la vidéo
```bash
bash pipeline/setup.sh                      # installe les outils + la voix (≈ 2 min la 1re fois)
python3 pipeline/make.py contenu/<date>_<type>.json
```
- `TROP COURT` → ajouter du contenu (segments ou détails) et relancer. Minimum 62 s (monétisation TikTok).
- Ouvrir l'image de contrôle indiquée (`verif.jpg`) avec l'outil Read et vérifier : texte lisible, rien ne déborde
  des cartes, pas de faute. Corriger le JSON et relancer si besoin.

## 4. Mettre en ligne la vidéo
```bash
git add contenu videos historique.md
git commit -m "Vidéo du <date> : <type> — <sujet>"
git -c push.negotiate=true push origin main
```
Ajouter d'abord dans `historique.md` la ligne du jour (date, type, sujet ou liste courte des 10 réponses).
Vérifier que `https://raw.githubusercontent.com/LaQlture/la-qlture-videos/main/videos/<date>_<type>.mp4`
répond 200 (`curl -sIL`).

## 5. Programmer sur Buffer
- `get_account` → organisation « My organization » + heure actuelle (pour le décalage horaire : +01:00 l'hiver, +02:00 l'été).
- `list_channels` → chaîne TikTok **la.qlture**.
- `create_post` : `channelId` TikTok, `mode: customScheduled`, `dueAt: <date>T12:00:00+01:00` (ou +02:00),
  `schedulingType: automatic`, `text` = `legende`, `assets: [{video: {url: <lien raw>}}]`,
  `metadata: {tiktok: {isAiGenerated: true}}` (case « contenu généré par IA » **cochée** depuis le 27/11 :
  la voix est une IA, et les vidéos publiées avec la case décochée faisaient 0 vue).
- Si une chaîne **YouTube** est connectée : même vidéo en `metadata.youtube` `{type: "short", title: <titre ≤ 90 car. + #shorts>,
  categoryId: "27", madeForKids: false}`.
- Si midi est déjà passé : programmer le lendemain 12 h 00 et le signaler.

## 6. En cas de problème
Ne jamais programmer une vidéo défectueuse ou un contenu non vérifié. Si une étape échoue après une nouvelle tentative,
s'arrêter et envoyer un message clair à l'utilisateur (ce qui a échoué, ce qui reste à faire).
Terminer par un court résumé : type, sujet, durée, heure de publication.
