package migrations

import (
	"github.com/pocketbase/pocketbase/core"
	m "github.com/pocketbase/pocketbase/migrations"
)

func init() {
	m.Register(func(app core.App) error {
		pv, err := app.FindCollectionByNameOrId("platform_variants")
		if err != nil {
			return err
		}

		field := pv.Fields.GetByName("publish_status")
		if field != nil {
			if selectField, ok := field.(*core.SelectField); ok {
				selectField.Values = []string{"draft", "approved", "scheduled", "published", "failed"}
			}
		}

		return app.Save(pv)
	}, func(app core.App) error {
		pv, err := app.FindCollectionByNameOrId("platform_variants")
		if err != nil {
			return err
		}

		field := pv.Fields.GetByName("publish_status")
		if field != nil {
			if selectField, ok := field.(*core.SelectField); ok {
				selectField.Values = []string{"draft", "scheduled", "published", "failed"}
			}
		}

		return app.Save(pv)
	})
}
