"""Zammad client helper tools.

This file reimplements the same helpers provided by the project's top-level
``zammad_client.py`` but as a first-class module inside the
``ticketing.tools`` package so other modules can import it directly.

It intentionally mirrors the top-level reference implementation and aims to be
robust against minor differences in Zammad client wrapper implementations.
"""

import os
import json
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

try:
	from zammad_py import ZammadAPI
except Exception as e:
	raise ImportError("zammad_py library is required. Install it in your environment.") from e

def init_zammad_client() -> Any:
	"""Create and return a ZammadAPI client object using environment variables.

	This internal helper is used by the module functions to create a fresh
	client on each call. It does NOT register the client in the ADK
	`_CLIENT_REGISTRY` (that registry is used by the ADK-facing
	`init_zammad_client`).
	"""
	url_base = os.getenv("zammad_url")
	if not url_base:
		raise EnvironmentError(f"Environment variable `zammad_url` is not set")
	url = url_base.rstrip("/") + "/api/v1/"
	username = os.getenv("zammad_username")
	password = os.getenv("zammad_password")
	return ZammadAPI(url=url, username=username, password=password)

def _collect_pages(first_page) -> List[Any]:
	items: List[Any] = []
	page = first_page
	if not page:
		return items
	try:
		items.extend(page)
	except TypeError:
		# single object
		items.append(page)

	while hasattr(page, "next_page") and callable(getattr(page, "next_page")):
		page = page.next_page()
		if not page:
			break
		try:
			items.extend(page)
		except TypeError:
			items.append(page)

	return items

def get_all_tickets() -> List[Dict[str, Any]]:
	"""Fetch all tickets. A Zammad client is created internally for this call.

	Returns a list of ticket dicts.
	"""
	client = init_zammad_client()
	page = client.ticket.all()
	return _collect_pages(page)

def get_ticket(ticket_id: int) -> Dict[str, Any]:
	"""Fetch a single ticket by `ticket_id`. A Zammad client is created internally."""
	client = init_zammad_client()
	return client.ticket.find(ticket_id)

def get_ticket_articles(ticket_id: int) -> List[Dict[str, Any]]:
	# Some client implementations ignore the ticket_id parameter. Fetch all articles
	# and filter by `ticket_id` to ensure we only return articles for the requested ticket.
	client = init_zammad_client()
	try:
		page = client.ticket_article.all()
	except TypeError:
		# Fallback: some clients expect positional args; ignore and fetch all
		page = client.ticket_article.all()

	all_articles = _collect_pages(page)
	return [a for a in all_articles if a.get("ticket_id") == ticket_id]

def get_all_articles() -> List[Dict[str, Any]]:
	"""Fetch all ticket articles (paginated) and return as a list."""
	client = init_zammad_client()
	page = client.ticket_article.all()
	return _collect_pages(page)

def create_ticket(ticket_data: Dict[str, Any]) -> Dict[str, Any]:
	"""Create a new ticket in Zammad.

	A Zammad client is created internally for this call.
	"""
	client = init_zammad_client()
	try:
		return client.ticket.create(params=ticket_data)
	except TypeError:
		# Some client wrappers accept positional args
		return client.ticket.create(ticket_data)

def get_ticket_details(ticket_id: int, include_attachments: bool = True) -> Dict[str, Any]:
	"""Return a consolidated view for a ticket: ticket data, articles and attachments metadata.

	A Zammad client is created internally for this call.
	"""
	client = init_zammad_client()
	ticket = None
	try:
		ticket = get_ticket(ticket_id, )
	except Exception as e:
		ticket = {"id": ticket_id, "error": str(e)}

	# Prefer fetching all articles and filtering to avoid client inconsistencies
	try:
		all_articles = get_all_articles()
		articles = [a for a in all_articles if a.get("ticket_id") == ticket_id]
	except Exception:
		# fallback to ticket-scoped call
		try:
			articles = get_ticket_articles(ticket_id, )
		except Exception:
			articles = []

	attachments_map = {}
	if include_attachments:
		for art in articles:
			aid = art.get("id")
			try:
				atts = list_article_attachments(ticket_id, aid, )
			except Exception:
				atts = []
			attachments_map[aid] = atts

	return {"ticket": ticket, "articles": articles, "attachments": attachments_map}

def set_ticket_state(ticket_id: int, state: Optional[str] = None, state_id: Optional[int] = None) -> Dict[str, Any]:
	"""Update the ticket's state. Accepts either a state name or a state_id.

	A Zammad client is created internally for this call.
	"""
	client = init_zammad_client()
	params = {}
	if state_id is not None:
		params["state_id"] = state_id
	if state is not None:
		# some APIs accept `state` or `state_id`; we'll include both where possible
		params["state"] = state

	if not params:
		raise ValueError("Either state or state_id must be provided")

	try:
		return client.ticket.update(id=ticket_id, params=params)
	except TypeError:
		# fallback if client expects positional args
		return client.ticket.update(ticket_id, params)

def set_ticket_priority(ticket_id: int, priority_id: Optional[int] = None, priority_name: Optional[str] = None) -> Dict[str, Any]:
	"""Set or update a ticket's priority by id or name.

	A Zammad client is created internally for this call.
	"""
	client = init_zammad_client()

	if priority_id is None and priority_name is None:
		raise ValueError("Either priority_id or priority_name must be provided")

	# Resolve name to id if needed
	if priority_id is None and priority_name is not None:
		try:
			page = client.ticket_priority.all()
			priorities = _collect_pages(page)
			for p in priorities:
				if str(p.get("name", "")).lower() == str(priority_name).lower():
					priority_id = p.get("id")
					break
		except Exception:
			priority_id = None

	if priority_id is None:
		raise ValueError("Could not resolve priority id; provide a valid priority_id or priority_name")

	params = {"priority_id": priority_id}
	try:
		return client.ticket.update(id=ticket_id, params=params)
	except TypeError:
		return client.ticket.update(ticket_id, params)


def list_article_attachments(ticket_id: int, article_id: int) -> List[Dict[str, Any]]:
	"""Return a list of attachment dicts with at least `id` and `filename` when possible.

	Tries multiple ways to discover attachments because different Zammad setups expose
	attachment metadata differently.
	"""
	client = init_zammad_client()

	# First try the article object itself
	try:
		art = client.ticket_article.find(ticket_id=ticket_id, id=article_id)
		if art:
			# art may contain an `attachments` list
			att = art.get("attachments") if isinstance(art, dict) else None
			if att:
				return att
	except Exception:
		pass

	# Try listing via ticket_article_attachment endpoint if available
	attachments = []
	try:
		if hasattr(client, "ticket_article_attachment"):
			page = None
			try:
				page = client.ticket_article_attachment.all(ticket_id=ticket_id, article_id=article_id)
			except TypeError:
				# some clients use positional args
				try:
					page = client.ticket_article_attachment.all(ticket_id, article_id)
				except Exception:
					page = None

			if page:
				attachments = _collect_pages(page)
				return attachments
	except Exception:
		pass

	# As a last resort, try to fetch the article by its id and inspect its fields
	try:
		art2 = client.ticket_article.find(article_id)
		if isinstance(art2, dict):
			for key in ("attachment_ids", "attachments_ids", "attachments"):
				if key in art2 and art2[key]:
					vals = art2[key]
					if isinstance(vals, list):
						out = []
						for v in vals:
							if isinstance(v, dict):
								out.append(v)
							else:
								out.append({"id": v, "filename": f"attachment_{v}"})
						return out
	except Exception:
		pass

	return []

def download_attachment(attachment_id: int, ticket_id: int, article_id: int, dest_path: str) -> Path:
	"""Download an attachment to `dest_path`.

	A Zammad client is created internally for this call. `dest_path` should be
	a string (helps with ADK automatic function calling); it will be converted
	to a `Path` internally.
	"""
	client = init_zammad_client()
	# convert string path to Path to preserve existing behavior
	dest_path = Path(dest_path)

	# Try a few different download call patterns depending on client implementation
	last_error = None
	resp = None
	callers = []
	if hasattr(client, "ticket_article_attachment"):
		callers.append(lambda: client.ticket_article_attachment.download(id=attachment_id, ticket_id=ticket_id, article_id=article_id))
		callers.append(lambda: client.ticket_article_attachment.download(attachment_id, ticket_id, article_id))
	if hasattr(client, "attachment"):
		callers.append(lambda: client.attachment.download(id=attachment_id))
		callers.append(lambda: client.attachment.download(attachment_id))

	# Generic fallback: try top-level download methods
	callers.append(lambda: getattr(client, "download", lambda *a, **k: None)())

	for c in callers:
		try:
			resp = c()
			if resp:
				break
		except Exception as e:
			last_error = e

	if not resp:
		raise RuntimeError(f"No download method returned data. Last error: {last_error}")

	# Extract bytes from response
	if isinstance(resp, (bytes, bytearray)):
		data = bytes(resp)
	elif isinstance(resp, dict):
		# Some clients return {"data": "base64...", "filename": "..."}
		if "data" in resp:
			try:
				data = base64.b64decode(resp["data"])
			except Exception:
				data = json.dumps(resp).encode()
		elif "file" in resp and isinstance(resp["file"], (bytes, bytearray)):
			data = bytes(resp["file"])
		else:
			data = json.dumps(resp).encode()
	elif hasattr(resp, "read"):
		data = resp.read()
	else:
		try:
			data = json.dumps(resp).encode()
		except Exception:
			data = b""

	dest_path.parent.mkdir(parents=True, exist_ok=True)
	with open(dest_path, "wb") as f:
		f.write(data)

	return dest_path


def send_message_to_ticket(ticket_id: int,
						 message: str,
						 subject: Optional[str] = None,
						 author_id: Optional[int] = None,
						 internal: bool = False,
						 article_type: Optional[str] = None,
						 additional_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
	"""Add a message (article) to an existing ticket.

	This helper tries multiple client call patterns to be tolerant of different
	Zammad client wrapper implementations. It returns the response from the
	client when a call succeeds.

	Parameters:
	- `ticket_id`: ID of the ticket to add the message to.
	- `message`: The article body/content.
	- `subject`: Optional subject/title for the article.
	- `author_id`: Optional id of the user creating the article.
	- `internal`: If True, the article will be internal (private) where supported.
	- `article_type`: Optional type/name for the article (e.g. 'note', 'reply').
	- `additional_params`: Dict of any extra params to pass through to the API.

	Returns the raw client response (often a dict) on success.
	"""
	client = init_zammad_client()
	params: Dict[str, Any] = {"ticket_id": ticket_id, "body": message, "internal": internal}
	if subject is not None:
		params["subject"] = subject
	if author_id is not None:
		params["author_id"] = author_id
	if article_type is not None:
		params["type"] = article_type
	if additional_params:
		params.update(additional_params)

	last_error = None
	# Try several common call signatures to support different client wrappers
	callers = []
	if hasattr(client, "ticket_article"):
		callers.append(lambda: client.ticket_article.create(params=params))
		callers.append(lambda: client.ticket_article.create(params))
		callers.append(lambda: client.ticket_article.create(ticket_id, params))
		callers.append(lambda: client.ticket_article.create(**params))

	# Some wrappers provide creation via the ticket endpoint
	callers.append(lambda: getattr(client, "ticket", None) and client.ticket.update(id=ticket_id, params={"article": params}))
	callers.append(lambda: getattr(client, "ticket", None) and client.ticket.update(ticket_id, {"article": params}))

	for c in callers:
		try:
			resp = c()
			if resp:
				return resp
		except TypeError as te:
			last_error = te
			continue
		except Exception as e:
			last_error = e
			continue

	raise RuntimeError(f"Could not create ticket article. Last error: {last_error}")