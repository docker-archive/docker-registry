# -*- coding: utf-8 -*-

import blinker


_signals = blinker.Namespace()

# Triggered when a repository is modified (registry/index.py)
repository_created = _signals.signal('repository-created')
repository_updated = _signals.signal('repository-updated')
repository_deleted = _signals.signal('repository-deleted')

# Triggered when a tag is modified (registry/tags.py)
tag_created = _signals.signal('tag-created')
tag_deleted = _signals.signal('tag-deleted')

# Triggered after all put_image_json validations have passed but before
# actually storing anything. Any non-None return value from the signalled
# subscribers will result in the put_image_json operation being cancelled.
before_put_image_json = _signals.signal('before-put-image-json')
