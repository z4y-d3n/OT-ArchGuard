# Synthetic schema fixtures

All data is invented. No hardware, network or external reference is required.

| File | Expected contract |
| --- | --- |
| minimal-valid.yaml | Two endpoints, one transport, permit, listener and independent requirement |
| invalid-missing-reference.yaml | invalid_input / MISSING_REFERENCE at $.transport_edges[0].destination_interface_id |
| invalid-interface-placement.yaml | invalid_input / INVALID_PLACEMENT at $.interfaces[0].placement_zone_id |
| unsupported-model.yaml | unsupported_model / UNSUPPORTED_CONDUIT at $.conduits[1].zone_ids |
| boundary-device.yaml | One device owned by dmz, explicit enterprise/dmz/control attachments and directed forwarding |

See [the example](../../docs/boundary-device-example.md). The boundary fixture has
eight passing intents. support_scope has ten non-self queries, four reachable
observation intervals and four destination assets. Test helpers use safe YAML
only for trusted fixtures; production uses its separate bounded event loader.
