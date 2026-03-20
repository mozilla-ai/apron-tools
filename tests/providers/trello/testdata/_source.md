# Test data sources

Fixtures derived from the Trello REST API documentation at
<https://developer.atlassian.com/cloud/trello/rest/>.

Field names and structure match the 200 response examples from:

- `GET /members/{id}/boards` — list_boards.json
- `GET /boards/{id}/lists` — list_lists.json
- `GET /lists/{id}/cards` — list_cards.json
- `GET /cards/{id}` — get_card.json
- `POST /cards` — create_card.json
- `PUT /cards/{id}` — move_card.json, set_due_date.json
