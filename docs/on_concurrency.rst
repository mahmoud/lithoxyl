On Concurrency, Crossing, and Continuity
========================================

oOne of the biggest challenges for developers is maintaining log
continuity across operations.

Lithoxyl solves this within the same process with the
Context.get_parent hook, the default of which is configured for
synchronous operation.

Beyond this, concurrency runs a huge gamut. There are basic cases and
very, very advanced cases. Lithoxyl is foremost a developer interface
to logging. Even if it were possible, Lithoxyl does not aim to build
in solutions to every concurrency use case.  Lithoxyl provides what it
can, but it's up to framework developers to adapt Lithoxyl more
completely.

One option is to solve it at a higher level, IDs that are used to
correlate and collate actions. Lithoxyl provides a few helpful values
in this domain:

* context.PROCESS_GUID
* context.get_context().context_guid
* Logger.logger_guid and logger.logger_id
* Action.action_id
* sensible.get_action_guid

GUIDs are opaque values with uniqueness assurance. They are similar to
UUIDs, but are denser (base64, not hex) for smaller logs and faster to
generate (by about 20x). The biggest application I've worked on, in
terms of application logging, generated well over 100GB per day. Every
byte matters.
