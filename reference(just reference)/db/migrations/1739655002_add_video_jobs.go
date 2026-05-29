package migrations

import (
	"encoding/json"

	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		videoJobsJSON := `{
  "id": "videojobs00000",
  "name": "video_jobs",
  "type": "base",
  "system": false,
  "listRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "viewRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "createRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "updateRule": null,
  "deleteRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
  "options": {},
  "fields": [
    {
      "system": false,
      "id": "vj_workspace_id",
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
      "id": "vj_requested_by",
      "name": "requested_by",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 255,
      "pattern": ""
    },
    {
      "system": false,
      "id": "vj_status",
      "name": "status",
      "type": "select",
      "required": true,
      "unique": false,
      "values": ["queued", "claimed", "rendering", "uploading", "done", "failed"],
      "maxSelect": 1
    },
    {
      "system": false,
      "id": "vj_priority",
      "name": "priority",
      "type": "number",
      "required": false,
      "unique": false,
      "min": null,
      "max": null
    },
    {
      "system": false,
      "id": "vj_input_json",
      "name": "input_json",
      "type": "json",
      "required": true,
      "unique": false,
      "maxSize": 2000000
    },
    {
      "system": false,
      "id": "vj_input_images",
      "name": "input_images",
      "type": "file",
      "required": false,
      "unique": false,
      "maxSelect": 10,
      "maxSize": 104857600,
      "mimeTypes": ["image/jpeg", "image/png", "image/webp"]
    },
    {
      "system": false,
      "id": "vj_input_music",
      "name": "input_music",
      "type": "file",
      "required": false,
      "unique": false,
      "maxSelect": 1,
      "maxSize": 52428800,
      "mimeTypes": ["audio/mpeg", "audio/mp3", "audio/wav"]
    },
    {
      "system": false,
      "id": "vj_input_logo",
      "name": "input_logo",
      "type": "file",
      "required": false,
      "unique": false,
      "maxSelect": 1,
      "maxSize": 10485760,
      "mimeTypes": ["image/jpeg", "image/png", "image/webp"]
    },
    {
      "system": false,
      "id": "vj_variant_name",
      "name": "variant_name",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 10,
      "pattern": ""
    },
    {
      "system": false,
      "id": "vj_output_video",
      "name": "output_video",
      "type": "file",
      "required": false,
      "unique": false,
      "maxSelect": 1,
      "maxSize": 524288000,
      "mimeTypes": ["video/mp4"]
    },
    {
      "system": false,
      "id": "vj_thumbnail",
      "name": "thumbnail",
      "type": "file",
      "required": false,
      "unique": false,
      "maxSelect": 1,
      "maxSize": 5242880,
      "mimeTypes": ["image/jpeg", "image/png"]
    },
    {
      "system": false,
      "id": "vj_progress",
      "name": "progress",
      "type": "number",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 100
    },
    {
      "system": false,
      "id": "vj_progress_stage",
      "name": "progress_stage",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 100,
      "pattern": ""
    },
    {
      "system": false,
      "id": "vj_attempt_count",
      "name": "attempt_count",
      "type": "number",
      "required": false,
      "unique": false,
      "min": 0,
      "max": null
    },
    {
      "system": false,
      "id": "vj_max_attempts",
      "name": "max_attempts",
      "type": "number",
      "required": false,
      "unique": false,
      "min": 1,
      "max": null
    },
    {
      "system": false,
      "id": "vj_worker_id",
      "name": "worker_id",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 255,
      "pattern": ""
    },
    {
      "system": false,
      "id": "vj_lease_until",
      "name": "lease_until",
      "type": "date",
      "required": false,
      "unique": false,
      "min": "",
      "max": ""
    },
    {
      "system": false,
      "id": "vj_error_message",
      "name": "error_message",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 5000,
      "pattern": ""
    },
    {
      "system": false,
      "id": "vj_render_duration_ms",
      "name": "render_duration_ms",
      "type": "number",
      "required": false,
      "unique": false,
      "min": 0,
      "max": null
    },
    {
      "system": false,
      "id": "vj_idempotency_key",
      "name": "idempotency_key",
      "type": "text",
      "required": false,
      "unique": true,
      "min": 0,
      "max": 255,
      "pattern": ""
    }
  ]
}`

		var collection core.Collection
		if err := json.Unmarshal([]byte(videoJobsJSON), &collection); err != nil {
			return err
		}

		// Delete if already exists (for idempotency)
		if existing, err := app.FindCollectionByNameOrId("video_jobs"); err == nil {
			if err := app.Delete(existing); err != nil {
				return err
			}
		}

		// Pass 1: Create without rules (avoids relation validation issues
		// and ensures system fields like created/updated are initialized)
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
		collection, err := app.FindCollectionByNameOrId("video_jobs")
		if err != nil {
			return nil
		}
		return app.Delete(collection)
	})
}
