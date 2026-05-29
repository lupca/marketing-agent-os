package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

// This migration adds fields for the multi-format content system:
// - master_contents: metadata (JSON), content_brief_id (relation)
// - platform_variants: content_type (select)
func init() {
	m.Register(func(app core.App) error {
		// 1. Add metadata + content_brief_id to master_contents
		mc, err := app.FindCollectionByNameOrId("master_contents")
		if err != nil {
			return err
		}

		if mc.Fields.GetByName("metadata") == nil {
			mc.Fields.Add(&core.JSONField{
				Name:     "metadata",
				Required: false,
			})
		}

		if mc.Fields.GetByName("content_brief_id") == nil {
			mc.Fields.Add(&core.RelationField{
				Name:          "content_brief_id",
				Required:      false,
				CollectionId:  "contentbriefs0",
				CascadeDelete: false,
				MaxSelect:     1,
			})
		}

		if err := app.Save(mc); err != nil {
			return err
		}

		// 2. Add content_type to platform_variants
		pv, err := app.FindCollectionByNameOrId("platform_variants")
		if err != nil {
			return err
		}

		if pv.Fields.GetByName("content_type") == nil {
			pv.Fields.Add(&core.SelectField{
				Name:     "content_type",
				Required: false,
				Values:   []string{"text", "video_script", "carousel", "story"},
				MaxSelect: 1,
			})
		}

		return app.Save(pv)
	}, func(app core.App) error {
		// Revert: Remove added fields
		mc, err := app.FindCollectionByNameOrId("master_contents")
		if err == nil {
			mc.Fields.RemoveByName("metadata")
			mc.Fields.RemoveByName("content_brief_id")
			app.Save(mc)
		}

		pv, err := app.FindCollectionByNameOrId("platform_variants")
		if err == nil {
			pv.Fields.RemoveByName("content_type")
			app.Save(pv)
		}

		return nil
	})
}
