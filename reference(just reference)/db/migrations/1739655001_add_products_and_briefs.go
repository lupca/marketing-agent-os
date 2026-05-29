package migrations

import (
	"encoding/json"

	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		// ============================================================
		// 1. Create products_services collection
		// ============================================================
		productsJSON := `{
  "id": "productservice",
  "name": "products_services",
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
      "id": "ps_workspace_id",
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
      "id": "ps_brand_id",
      "name": "brand_id",
      "type": "relation",
      "required": true,
      "unique": false,
      "collectionId": "brandidentities",
      "cascadeDelete": false,
      "minSelect": null,
      "maxSelect": 1,
      "displayFields": []
    },
    {
      "system": false,
      "id": "ps_name",
      "name": "name",
      "type": "text",
      "required": true,
      "unique": false,
      "min": 1,
      "max": 255,
      "pattern": ""
    },
    {
      "system": false,
      "id": "ps_description",
      "name": "description",
      "type": "editor",
      "required": false,
      "unique": false,
      "convertUrls": false
    },
    {
      "system": false,
      "id": "ps_usp",
      "name": "usp",
      "type": "editor",
      "required": false,
      "unique": false,
      "convertUrls": false
    },
    {
      "system": false,
      "id": "ps_key_features",
      "name": "key_features",
      "type": "json",
      "required": false,
      "unique": false
    },
    {
      "system": false,
      "id": "ps_key_benefits",
      "name": "key_benefits",
      "type": "json",
      "required": false,
      "unique": false
    },
    {
      "system": false,
      "id": "ps_default_offer",
      "name": "default_offer",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 1000,
      "pattern": ""
    }
  ]
}`

		var productsCollection core.Collection
		if err := json.Unmarshal([]byte(productsJSON), &productsCollection); err != nil {
			return err
		}

		// Delete if already exists (for idempotency)
		if existing, err := app.FindCollectionByNameOrId("products_services"); err == nil {
			if err := app.Delete(existing); err != nil {
				return err
			}
		}

		// Pass 1: Create without rules
		listRule := productsCollection.ListRule
		viewRule := productsCollection.ViewRule
		createRule := productsCollection.CreateRule
		updateRule := productsCollection.UpdateRule
		deleteRule := productsCollection.DeleteRule

		productsCollection.ListRule = nil
		productsCollection.ViewRule = nil
		productsCollection.CreateRule = nil
		productsCollection.UpdateRule = nil
		productsCollection.DeleteRule = nil

		if err := app.Save(&productsCollection); err != nil {
			return err
		}

		// Pass 2: Set rules
		productsCollection.ListRule = listRule
		productsCollection.ViewRule = viewRule
		productsCollection.CreateRule = createRule
		productsCollection.UpdateRule = updateRule
		productsCollection.DeleteRule = deleteRule

		if err := app.Save(&productsCollection); err != nil {
			return err
		}

		// ============================================================
		// 2. Create content_briefs collection
		// ============================================================
		briefsJSON := `{
  "id": "contentbriefs0",
  "name": "content_briefs",
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
      "id": "cb_workspace_id",
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
      "id": "cb_campaign_id",
      "name": "campaign_id",
      "type": "relation",
      "required": true,
      "unique": false,
      "collectionId": "marketingcampai",
      "cascadeDelete": true,
      "minSelect": null,
      "maxSelect": 1,
      "displayFields": []
    },
    {
      "system": false,
      "id": "cb_angle_name",
      "name": "angle_name",
      "type": "text",
      "required": true,
      "unique": false,
      "min": 1,
      "max": 255,
      "pattern": ""
    },
    {
      "system": false,
      "id": "cb_funnel_stage",
      "name": "funnel_stage",
      "type": "select",
      "required": true,
      "unique": false,
      "maxSelect": 1,
      "values": [
        "Awareness",
        "Consideration",
        "Conversion",
        "Retention"
      ]
    },
    {
      "system": false,
      "id": "cb_psychological_angle",
      "name": "psychological_angle",
      "type": "select",
      "required": true,
      "unique": false,
      "maxSelect": 1,
      "values": [
        "Fear",
        "Emotion",
        "Logic",
        "Social Proof",
        "Urgency",
        "Curiosity"
      ]
    },
    {
      "system": false,
      "id": "cb_pain_point_focus",
      "name": "pain_point_focus",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 1000,
      "pattern": ""
    },
    {
      "system": false,
      "id": "cb_key_message_variation",
      "name": "key_message_variation",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 2000,
      "pattern": ""
    },
    {
      "system": false,
      "id": "cb_call_to_action_direction",
      "name": "call_to_action_direction",
      "type": "text",
      "required": false,
      "unique": false,
      "min": 0,
      "max": 500,
      "pattern": ""
    },
    {
      "system": false,
      "id": "cb_brief",
      "name": "brief",
      "type": "editor",
      "required": false,
      "unique": false,
      "convertUrls": false
    }
  ]
}`

		var briefsCollection core.Collection
		if err := json.Unmarshal([]byte(briefsJSON), &briefsCollection); err != nil {
			return err
		}

		// Delete if already exists
		if existing, err := app.FindCollectionByNameOrId("content_briefs"); err == nil {
			if err := app.Delete(existing); err != nil {
				return err
			}
		}

		// Pass 1: Create without rules
		listRule = briefsCollection.ListRule
		viewRule = briefsCollection.ViewRule
		createRule = briefsCollection.CreateRule
		updateRule = briefsCollection.UpdateRule
		deleteRule = briefsCollection.DeleteRule

		briefsCollection.ListRule = nil
		briefsCollection.ViewRule = nil
		briefsCollection.CreateRule = nil
		briefsCollection.UpdateRule = nil
		briefsCollection.DeleteRule = nil

		if err := app.Save(&briefsCollection); err != nil {
			return err
		}

		// Pass 2: Set rules
		briefsCollection.ListRule = listRule
		briefsCollection.ViewRule = viewRule
		briefsCollection.CreateRule = createRule
		briefsCollection.UpdateRule = updateRule
		briefsCollection.DeleteRule = deleteRule

		if err := app.Save(&briefsCollection); err != nil {
			return err
		}

		// ============================================================
		// 3. Add product_id field to marketing_campaigns
		// ============================================================
		campaigns, err := app.FindCollectionByNameOrId("marketing_campaigns")
		if err != nil {
			return err
		}

		// Only add if field doesn't exist yet
		if campaigns.Fields.GetByName("product_id") == nil {
			campaigns.Fields.Add(&core.RelationField{
				Name:          "product_id",
				Required:      false,
				CollectionId:  "productservice",
				CascadeDelete: false,
				MaxSelect:     1,
			})
			if err := app.Save(campaigns); err != nil {
				return err
			}
		}

		return nil
	}, func(app core.App) error {
		// Revert: Remove the new collections and field
		if existing, err := app.FindCollectionByNameOrId("content_briefs"); err == nil {
			if err := app.Delete(existing); err != nil {
				return err
			}
		}
		if existing, err := app.FindCollectionByNameOrId("products_services"); err == nil {
			if err := app.Delete(existing); err != nil {
				return err
			}
		}

		// Remove product_id field from marketing_campaigns
		campaigns, err := app.FindCollectionByNameOrId("marketing_campaigns")
		if err == nil {
			if field := campaigns.Fields.GetByName("product_id"); field != nil {
				campaigns.Fields.RemoveById(field.GetId())
				_ = app.Save(campaigns)
			}
		}

		return nil
	})
}
