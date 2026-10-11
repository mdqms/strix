"""Fork integrations with separate external services (Apache-2.0).

Modules here talk to standalone services over the network. They import no code
from those services; in particular the MiroFish integration never imports or
vendors MiroFish (which is AGPL-3.0) — it only calls a separate MiroFish process
over HTTP. See strix/integrations/mirofish.py and deploy/mirofish/README.md.
"""
