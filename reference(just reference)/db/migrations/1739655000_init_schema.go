package migrations

import (
	"encoding/json"

	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		// 1. Add 'role' field to 'users' collection
		users, err := app.FindCollectionByNameOrId("users")
		if err != nil {
			return err
		}

		// Check if field already exists to avoid errors on re-run (though this is a fresh init migration)
		if users.Fields.GetByName("role") == nil {
			users.Fields.Add(&core.SelectField{
				Name:        "role",
				Required:    false,
				Presentable: false,
				MaxSelect:   1,
				Values:      []string{"admin", "manager", "member", "viewer"},
			})
			if err := app.Save(users); err != nil {
				return err
			}
		}

		// 2. Import the rest of the schema from JSON
		// We define the JSON inline here to ensure the migration is self-contained and doesn't depend on external files at runtime.
		// This JSON matches exactly the content of docs/marketing_schema.json
		schemaJSON := `[
  {
    "id": "workspaces00000",
    "name": "workspaces",
    "type": "base",
    "system": false,
    "listRule": "@request.auth.id != '' && (owner_id = @request.auth.id || members.id ?= @request.auth.id)",
    "viewRule": "@request.auth.id != '' && (owner_id = @request.auth.id || members.id ?= @request.auth.id)",
    "createRule": "@request.auth.id != ''",
    "updateRule": "@request.auth.id != '' && (owner_id = @request.auth.id || members.id ?= @request.auth.id)",
    "deleteRule": "@request.auth.id != '' && owner_id = @request.auth.id",
    "options": {},
    "fields": [
      {
        "system": false,
        "id": "workspaces_name",
        "name": "name",
        "type": "text",
        "required": true,
        "unique": true,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "workspaces_owner_id",
        "name": "owner_id",
        "type": "relation",
        "required": true,
        "unique": false,
        "collectionId": "_pb_users_auth_",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 1,
        "displayFields": []
      },
      {
        "system": false,
        "id": "workspaces_members",
        "name": "members",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "_pb_users_auth_",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 99999,
        "displayFields": []
      },
      {
        "system": false,
        "id": "workspaces_settings",
        "name": "settings",
        "type": "json",
        "required": false,
        "unique": false
      }
    ]
  },
  {
    "id": "brandidentities",
    "name": "brand_identities",
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
        "id": "brand_identities_workspace_id",
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
        "id": "brand_identities_brand_name",
        "name": "brand_name",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "brand_identities_core_messaging",
        "name": "core_messaging",
        "type": "json",
        "required": false,
        "unique": false
      },
      {
        "system": false,
        "id": "brand_identities_visual_assets",
        "name": "visual_assets",
        "type": "json",
        "required": false,
        "unique": false
      },
      {
        "system": false,
        "id": "brand_identities_voice_and_tone",
        "name": "voice_and_tone",
        "type": "editor",
        "required": false,
        "unique": false,
        "convertUrls": false
      },
      {
        "system": false,
        "id": "brand_identities_dos_and_donts",
        "name": "dos_and_donts",
        "type": "json",
        "required": false,
        "unique": false
      },
      {
        "system": false,
        "id": "brand_identities_content_pillars",
        "name": "content_pillars",
        "type": "json",
        "required": false,
        "unique": false
      }
    ]
  },
  {
    "id": "customerpersona",
    "name": "customer_personas",
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
        "id": "customer_personas_workspace_id",
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
        "id": "customer_personas_persona_name",
        "name": "persona_name",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "customer_personas_summary",
        "name": "summary",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": 2048,
        "pattern": ""
      },
      {
        "system": false,
        "id": "customer_personas_demographics",
        "name": "demographics",
        "type": "json",
        "required": false,
        "unique": false
      },
      {
        "system": false,
        "id": "customer_personas_psychographics",
        "name": "psychographics",
        "type": "json",
        "required": false,
        "unique": false
      }
    ]
  },
  {
    "id": "mediaassets0000",
    "name": "media_assets",
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
        "id": "media_assets_workspace_id",
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
        "id": "media_assets_file",
        "name": "file",
        "type": "file",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "maxSize": 104857600,
        "mimeTypes": [
          "image/jpeg",
          "image/png",
          "image/gif",
          "image/webp",
          "image/svg+xml",
          "video/mp4",
          "video/webm",
          "application/pdf",
          "application/msword",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ],
        "thumbs": [],
        "protected": false
      },
      {
        "system": false,
        "id": "media_assets_file_type",
        "name": "file_type",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "image",
          "video",
          "doc"
        ]
      },
      {
        "system": false,
        "id": "media_assets_aspect_ratio",
        "name": "aspect_ratio",
        "type": "select",
        "required": false,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "1:1",
          "16:9",
          "9:16",
          "4:5",
          "4:3",
          "N/A"
        ]
      },
      {
        "system": false,
        "id": "media_assets_tags",
        "name": "tags",
        "type": "json",
        "required": false,
        "unique": false
      }
    ]
  },
  {
    "id": "inspirationevts",
    "name": "inspiration_events",
    "type": "base",
    "system": false,
    "listRule": "@request.auth.id != '' && (workspace_id.members.id ?= @request.auth.id || workspace_id = '')",
    "viewRule": "@request.auth.id != '' && (workspace_id.members.id ?= @request.auth.id || workspace_id = '')",
    "createRule": "@request.auth.id != ''",
    "updateRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
    "deleteRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
    "options": {},
    "fields": [
      {
        "system": false,
        "id": "inspiration_events_workspace_id",
        "name": "workspace_id",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "workspaces00000",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 1,
        "displayFields": []
      },
      {
        "system": false,
        "id": "inspiration_events_event_name",
        "name": "event_name",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "inspiration_events_event_date",
        "name": "event_date",
        "type": "date",
        "required": false,
        "unique": false,
        "min": "",
        "max": ""
      },
      {
        "system": false,
        "id": "inspiration_events_type",
        "name": "type",
        "type": "select",
        "required": false,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "holiday",
          "industry_event",
          "company_milestone",
          "trend",
          "other"
        ]
      },
      {
        "system": false,
        "id": "inspiration_events_description",
        "name": "description",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "system": false,
        "id": "inspiration_events_suggested_angles",
        "name": "suggested_angles",
        "type": "json",
        "required": false,
        "unique": false
      }
    ]
  },
  {
    "id": "socialaccounts0",
    "name": "social_accounts",
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
        "id": "social_accounts_workspace_id",
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
        "id": "social_accounts_platform",
        "name": "platform",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "facebook",
          "instagram",
          "linkedin",
          "twitter",
          "tiktok",
          "youtube"
        ]
      },
      {
        "system": false,
        "id": "social_accounts_account_name",
        "name": "account_name",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "social_accounts_account_id",
        "name": "account_id",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "social_accounts_access_token",
        "name": "access_token",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "system": false,
        "id": "social_accounts_refresh_token",
        "name": "refresh_token",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "system": false,
        "id": "social_accounts_expires_at",
        "name": "expires_at",
        "type": "date",
        "required": false,
        "unique": false,
        "min": "",
        "max": ""
      }
    ]
  },
  {
    "id": "prompttemplates",
    "name": "prompt_templates",
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
        "id": "prompt_templates_workspace_id",
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
        "id": "prompt_templates_agent_role",
        "name": "agent_role",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "prompt_templates_template_text",
        "name": "template_text",
        "type": "editor",
        "required": true,
        "unique": false,
        "convertUrls": false
      }
    ]
  },
  {
    "id": "worksheets00000",
    "name": "worksheets",
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
        "id": "worksheets_workspace_id",
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
        "id": "worksheets_title",
        "name": "title",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "worksheets_event_id",
        "name": "event_id",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "inspirationevts",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 1,
        "displayFields": []
      },
      {
        "system": false,
        "id": "worksheets_brands",
        "name": "brandRefs",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "brandidentities",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 99999,
        "displayFields": []
      },
      {
        "system": false,
        "id": "worksheets_personas",
        "name": "customerRefs",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "customerpersona",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 99999,
        "displayFields": []
      },
      {
        "system": false,
        "id": "worksheets_status",
        "name": "status",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "draft",
          "processing",
          "completed",
          "archived"
        ]
      },
      {
        "system": false,
        "id": "worksheets_agent_context",
        "name": "agent_context",
        "type": "json",
        "required": false,
        "unique": false
      }
    ]
  },
  {
    "id": "marketingcampai",
    "name": "marketing_campaigns",
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
        "id": "marketing_campa_workspace_id",
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
        "id": "marketing_campa_worksheet_id",
        "name": "worksheet_id",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "worksheets00000",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 1,
        "displayFields": []
      },
      {
        "system": false,
        "id": "marketing_campa_name",
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
        "id": "marketing_campa_campaign_type",
        "name": "campaign_type",
        "type": "select",
        "required": false,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "awareness",
          "conversion",
          "retargeting",
          "newsletter",
          "social_series"
        ]
      },
      {
        "system": false,
        "id": "marketing_campa_status",
        "name": "status",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "planned",
          "active",
          "paused",
          "completed",
          "cancelled"
        ]
      },
      {
        "system": false,
        "id": "marketing_campa_budget",
        "name": "budget",
        "type": "number",
        "required": false,
        "unique": false,
        "min": 0,
        "max": null,
        "noDecimal": false
      },
      {
        "system": false,
        "id": "marketing_campa_kpi_targets",
        "name": "kpi_targets",
        "type": "json",
        "required": false,
        "unique": false
      },
      {
        "system": false,
        "id": "marketing_campa_start_date",
        "name": "start_date",
        "type": "date",
        "required": false,
        "unique": false,
        "min": "",
        "max": ""
      },
      {
        "system": false,
        "id": "marketing_campa_end_date",
        "name": "end_date",
        "type": "date",
        "required": false,
        "unique": false,
        "min": "",
        "max": ""
      }
    ]
  },
  {
    "id": "mastercontents0",
    "name": "master_contents",
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
        "id": "master_contents_workspace_id",
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
        "id": "master_contents_campaign_id",
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
        "id": "master_contents_core_message",
        "name": "core_message",
        "type": "editor",
        "required": false,
        "unique": false,
        "convertUrls": false
      },
      {
        "system": false,
        "id": "master_contents_primary_media",
        "name": "primaryMediaIds",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "mediaassets0000",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 99999,
        "displayFields": []
      },
      {
        "system": false,
        "id": "master_contents_approval_status",
        "name": "approval_status",
        "type": "select",
        "required": false,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "pending",
          "approved",
          "rejected",
          "revision_needed"
        ]
      }
    ]
  },
  {
    "id": "agentlogs000000",
    "name": "agent_logs",
    "type": "base",
    "system": false,
    "listRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
    "viewRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
    "createRule": "@request.auth.id != '' && workspace_id.members.id ?= @request.auth.id",
    "updateRule": "",
    "deleteRule": "",
    "options": {},
    "fields": [
      {
        "system": false,
        "id": "agent_logs_workspace_id",
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
        "id": "agent_logs_agent_name",
        "name": "agent_name",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "agent_logs_action",
        "name": "action",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "agent_logs_status",
        "name": "status",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "success",
          "failed",
          "pending"
        ]
      },
      {
        "system": false,
        "id": "agent_logs_tokens_used",
        "name": "tokens_used",
        "type": "number",
        "required": false,
        "unique": false,
        "min": 0,
        "max": null,
        "noDecimal": true
      },
      {
        "system": false,
        "id": "agent_logs_error_message",
        "name": "error_message",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": null,
        "pattern": ""
      }
    ]
  },
  {
    "id": "platformvariant",
    "name": "platform_variants",
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
        "id": "platform_variants_workspace_id",
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
        "id": "platform_variants_master_content_id",
        "name": "master_content_id",
        "type": "relation",
        "required": true,
        "unique": false,
        "collectionId": "mastercontents0",
        "cascadeDelete": true,
        "minSelect": null,
        "maxSelect": 1,
        "displayFields": []
      },
      {
        "system": false,
        "id": "platform_variants_platform",
        "name": "platform",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "facebook",
          "instagram",
          "linkedin",
          "twitter",
          "tiktok",
          "youtube",
          "blog",
          "email"
        ]
      },
      {
        "system": false,
        "id": "platform_variants_adapted_copy",
        "name": "adapted_copy",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "system": false,
        "id": "platform_variants_platform_media",
        "name": "platformMediaIds",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "mediaassets0000",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 99999,
        "displayFields": []
      },
      {
        "system": false,
        "id": "platform_variants_publish_status",
        "name": "publish_status",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "draft",
          "scheduled",
          "published",
          "failed"
        ]
      },
      {
        "system": false,
        "id": "platform_variants_scheduled_at",
        "name": "scheduled_at",
        "type": "date",
        "required": false,
        "unique": false,
        "min": "",
        "max": ""
      },
      {
        "system": false,
        "id": "platform_variants_published_at",
        "name": "published_at",
        "type": "date",
        "required": false,
        "unique": false,
        "min": "",
        "max": ""
      },
      {
        "system": false,
        "id": "platform_variants_platform_post_id",
        "name": "platform_post_id",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "system": false,
        "id": "platform_variants_metadata",
        "name": "metadata",
        "type": "json",
        "required": false,
        "unique": false
      },
      {
        "system": false,
        "id": "platform_variants_metric_views",
        "name": "metric_views",
        "type": "number",
        "required": false,
        "unique": false,
        "min": 0,
        "max": null,
        "noDecimal": true
      },
      {
        "system": false,
        "id": "platform_variants_metric_likes",
        "name": "metric_likes",
        "type": "number",
        "required": false,
        "unique": false,
        "min": 0,
        "max": null,
        "noDecimal": true
      },
      {
        "system": false,
        "id": "platform_variants_metric_shares",
        "name": "metric_shares",
        "type": "number",
        "required": false,
        "unique": false,
        "min": 0,
        "max": null,
        "noDecimal": true
      },
      {
        "system": false,
        "id": "platform_variants_metric_comments",
        "name": "metric_comments",
        "type": "number",
        "required": false,
        "unique": false,
        "min": 0,
        "max": null,
        "noDecimal": true
      }
    ]
  },
  {
    "id": "trackinglinks00",
    "name": "tracking_links",
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
        "id": "tracking_links_workspace_id",
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
        "id": "tracking_links_variant_id",
        "name": "variant_id",
        "type": "relation",
        "required": true,
        "unique": false,
        "collectionId": "platformvariant",
        "cascadeDelete": true,
        "minSelect": null,
        "maxSelect": 1,
        "displayFields": []
      },
      {
        "system": false,
        "id": "tracking_links_original_url",
        "name": "original_url",
        "type": "url",
        "required": true,
        "unique": false,
        "exceptDomains": [],
        "onlyDomains": []
      },
      {
        "system": false,
        "id": "tracking_links_short_url",
        "name": "short_url",
        "type": "url",
        "required": false,
        "unique": false,
        "exceptDomains": [],
        "onlyDomains": []
      },
      {
        "system": false,
        "id": "tracking_links_utm_source",
        "name": "utm_source",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "system": false,
        "id": "tracking_links_utm_campaign",
        "name": "utm_campaign",
        "type": "text",
        "required": false,
        "unique": false,
        "min": null,
        "max": null,
        "pattern": ""
      },
      {
        "system": false,
        "id": "tracking_links_click_count",
        "name": "click_count",
        "type": "number",
        "required": false,
        "unique": false,
        "min": 0,
        "max": null,
        "noDecimal": true
      }
    ]
  },
  {
    "id": "socialinteract0",
    "name": "social_interactions",
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
        "id": "social_interactions_workspace_id",
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
        "id": "social_interactions_variant_id",
        "name": "variant_id",
        "type": "relation",
        "required": true,
        "unique": false,
        "collectionId": "platformvariant",
        "cascadeDelete": true,
        "minSelect": null,
        "maxSelect": 1,
        "displayFields": []
      },
      {
        "system": false,
        "id": "social_interactions_platform_user_id",
        "name": "platform_user_id",
        "type": "text",
        "required": true,
        "unique": false,
        "min": 1,
        "max": 255,
        "pattern": ""
      },
      {
        "system": false,
        "id": "social_interactions_content",
        "name": "content",
        "type": "text",
        "required": true,
        "unique": false,
        "min": null,
        "max": 2048,
        "pattern": ""
      },
      {
        "system": false,
        "id": "social_interactions_sentiment",
        "name": "sentiment",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "positive",
          "neutral",
          "negative"
        ]
      },
      {
        "system": false,
        "id": "social_interactions_is_handled",
        "name": "is_handled",
        "type": "bool",
        "required": false,
        "unique": false
      }
    ]
  },
  {
    "id": "leads0000000000",
    "name": "leads",
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
        "id": "leads_workspace_id",
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
        "id": "leads_campaign_id",
        "name": "campaign_id",
        "type": "relation",
        "required": false,
        "unique": false,
        "collectionId": "marketingcampai",
        "cascadeDelete": false,
        "minSelect": null,
        "maxSelect": 1,
        "displayFields": []
      },
      {
        "system": false,
        "id": "leads_name",
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
        "id": "leads_email",
        "name": "email",
        "type": "email",
        "required": false,
        "unique": false,
        "exceptDomains": [],
        "onlyDomains": []
      },
      {
        "system": false,
        "id": "leads_phone",
        "name": "phone",
        "type": "text",
        "required": false,
        "unique": false,
        "min": 5,
        "max": 20,
        "pattern": ""
      },
      {
        "system": false,
        "id": "leads_source",
        "name": "source",
        "type": "select",
        "required": false,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "web",
          "social",
          "email",
          "referral",
          "other"
        ]
      },
      {
        "system": false,
        "id": "leads_status",
        "name": "status",
        "type": "select",
        "required": true,
        "unique": false,
        "maxSelect": 1,
        "values": [
          "new",
          "contacted",
          "qualified",
          "converted",
          "lost"
        ]
      }
    ]
  }
]
`

		collections := []*core.Collection{}
		if err := json.Unmarshal([]byte(schemaJSON), &collections); err != nil {
			return err
		}

		// Cleanup existing collections to ensure fresh start with correct IDs
		// We delete in a specific order to satisfy foreign key constraints (children first)
		collectionsToDelete := []string{
			"social_posts", "content_calendar_events", "campaign_tasks", // Legacy
			"leads", "social_interactions", "tracking_links", "platform_variants", "master_contents", // New Leaves
			"marketing_campaigns",
			"ideal_customer_profiles", // Legacy
			"brand_identities",
			"customer_personas",
			"media_assets",
			"worksheets",
			"inspiration_events",
			"prompt_templates",
			"social_accounts",
			"agent_logs",
			"workspaces",
		}

		for _, name := range collectionsToDelete {
			if existing, err := app.FindCollectionByNameOrId(name); err == nil {
				if err := app.Delete(existing); err != nil {
					return err
				}
			}
		}

		// Pass 1: Create collections with no rules (admin only)
		// This avoids validation errors for fields/relations that might not exist yet during the initial Save.
		for _, collection := range collections {
			// Cache rules
			listRule := collection.ListRule
			viewRule := collection.ViewRule
			createRule := collection.CreateRule
			updateRule := collection.UpdateRule
			deleteRule := collection.DeleteRule

			// Clear rules for first pass
			collection.ListRule = nil
			collection.ViewRule = nil
			collection.CreateRule = nil
			collection.UpdateRule = nil
			collection.DeleteRule = nil

			if err := app.Save(collection); err != nil {
				return err
			}

			// Restore rules
			collection.ListRule = listRule
			collection.ViewRule = viewRule
			collection.CreateRule = createRule
			collection.UpdateRule = updateRule
			collection.DeleteRule = deleteRule
		}

		// Pass 2: Update collections with rules
		for _, collection := range collections {
			if err := app.Save(collection); err != nil {
				return err
			}
		}

		return nil
	}, func(app core.App) error {
		// Revert not required as this is an init migration
		return nil
	})
}
