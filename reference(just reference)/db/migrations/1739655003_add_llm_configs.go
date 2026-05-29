package migrations

import (
	"encoding/json"

	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		llmConfigsJSON := `{
  "id": "llmconfigs00000",
  "name": "llm_configs",
  "type": "base",
  "system": false,
  "listRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "viewRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "createRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "updateRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "deleteRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "options": {},
  "fields": [
    {
      "system": false,
      "id": "lc_workspace_id",
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
      "id": "lc_provider",
      "name": "provider",
      "type": "select",
      "required": true,
      "unique": false,
      "values": ["gemini", "ollama"],
      "maxSelect": 1
    },
    {
      "system": false,
      "id": "lc_model_name",
      "name": "model_name",
      "type": "text",
      "required": true,
      "unique": false,
      "min": 0,
      "max": 255,
      "pattern": ""
    },
    {
      "system": false,
      "id": "lc_api_key",
      "name": "api_key",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 500,
      "pattern": ""
    },
    {
      "system": false,
      "id": "lc_base_url",
      "name": "base_url",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 500,
      "pattern": ""
    },
    {
      "system": false,
      "id": "lc_is_default",
      "name": "is_default",
      "type": "bool",
      "required": false,
      "unique": false
    }
  ]
}`

		var collection core.Collection
		if err := json.Unmarshal([]byte(llmConfigsJSON), &collection); err != nil {
			return err
		}

		// Delete if already exists (for idempotency)
		if existing, err := app.FindCollectionByNameOrId("llm_configs"); err == nil {
			if err := app.Delete(existing); err != nil {
				return err
			}
		}

		// Pass 1: Create without rules (avoids relation validation issues)
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
		collection, err := app.FindCollectionByNameOrId("llm_configs")
		if err != nil {
			return nil
		}
		return app.Delete(collection)
	})
}
