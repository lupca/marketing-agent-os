package migrations

import (
	"encoding/json"

	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		aiTracesJSON := `{
  "id": "aitraces00000",
  "name": "ai_traces",
  "type": "base",
  "system": false,
  "listRule": "@request.auth.id != ''",
  "viewRule": "@request.auth.id != ''",
  "createRule": "@request.auth.id != ''",
  "updateRule": "@request.auth.id != ''",
  "deleteRule": "@request.auth.id != ''",
  "options": {},
  "fields": [
    {
      "system": false,
      "id": "tr_workspace_id",
      "name": "workspace_id",
      "type": "relation",
      "required": true,
      "unique": false,
      "collectionId": "workspaces00000",
      "cascadeDelete": true,
      "minSelect": null,
      "maxSelect": 1,
      "displayFields": []
    },
    {
      "system": false,
      "id": "tr_campaign_id",
      "name": "campaign_id",
      "type": "relation",
      "required": false,
      "unique": false,
      "collectionId": "marketingcampai",
      "cascadeDelete": true,
      "minSelect": null,
      "maxSelect": 1,
      "displayFields": []
    },
    {
      "system": false,
      "id": "tr_agent_name",
      "name": "agent_name",
      "type": "text",
      "required": true,
      "unique": false,
      "min": 0,
      "max": 255,
      "pattern": ""
    },
    {
      "system": false,
      "id": "tr_turn_number",
      "name": "turn_number",
      "type": "number",
      "required": true,
      "unique": false
    },
    {
      "system": false,
      "id": "tr_input_prompt",
      "name": "input_prompt",
      "type": "text",
      "required": true,
      "unique": false
    },
    {
      "system": false,
      "id": "tr_output_response",
      "name": "output_response",
      "type": "text",
      "required": true,
      "unique": false
    },
    {
      "system": false,
      "id": "tr_prompt_tokens",
      "name": "prompt_tokens",
      "type": "number",
      "required": true,
      "unique": false
    },
    {
      "system": false,
      "id": "tr_completion_tokens",
      "name": "completion_tokens",
      "type": "number",
      "required": true,
      "unique": false
    },
    {
      "system": false,
      "id": "tr_execution_time_ms",
      "name": "execution_time_ms",
      "type": "number",
      "required": true,
      "unique": false
    },
    {
      "system": false,
      "id": "tr_status",
      "name": "status",
      "type": "text",
      "required": true,
      "unique": false,
      "min": 0,
      "max": 100,
      "pattern": ""
    }
  ]
}`

		var collection core.Collection
		if err := json.Unmarshal([]byte(aiTracesJSON), &collection); err != nil {
			return err
		}

		// Delete if already exists (for idempotency)
		if existing, err := app.FindCollectionByNameOrId("ai_traces"); err == nil {
			if err := app.Delete(existing); err != nil {
				return err
			}
		}

		// Pass 1: Create without rules
		listRule := collection.ListRule
		viewRule := collection.ViewRule
		createRule := collection.CreateRule
		updateRule := collection.UpdateRule
		deleteRule := collection.DeleteRule

		collection.ListRule = nil
		collection.ViewRule = nil
		collection.CreateRule = nil
		collection.UpdateRule = nil
		collection.DeleteRule = nil

		if err := app.Save(&collection); err != nil {
			return err
		}

		// Pass 2: Restore rules
		collection.ListRule = listRule
		collection.ViewRule = viewRule
		collection.CreateRule = createRule
		collection.UpdateRule = updateRule
		collection.DeleteRule = deleteRule

		return app.Save(&collection)
	}, func(app core.App) error {
		collection, err := app.FindCollectionByNameOrId("ai_traces")
		if err != nil {
			return nil
		}
		return app.Delete(collection)
	})
}
