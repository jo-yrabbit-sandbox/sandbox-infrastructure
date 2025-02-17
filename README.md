# Core infrastructure to serve multiple TG bots

## Overview

An API server with backend redis database which:
* Stores messages from multiple bots
* Allows clients to get stored messages
* Filter results by bot, state

```sh
Bot 1 ---> \
Bot 2 ---> API Server (EC2) ---> Redis (ElastiCache)
Bot 3 ---> /     ^
                 |
            Website (S3)
```

### API server

The api-server provides public endpoints for storing and fetching telegram messages.
So far, the only requirement is for payloads to be sent as json with the following schema.

```json
{
    "bot_id": "name of your bot",
    "message": {
        "state": "bot state (you define it)",
        "text": "the message text",
        "timestamp": "%Y-%m-%d_%H:%M:%S"
    }
}
```

### Bot platform

The infrastructure is designed to serve multiple bots created by different people from everywhere.
Developers will own their own source code in their own repo, and we just give you the resources to keep it running.
To begin, create your repo from this template [test-bot](https://github.com/tee-gee-bots/test-bot) and follow the onboarding instructions in the README.md.

### Deployment

The exciting part of this design is its automated deployment to AWS. Deployment details are fully managed by terraform infrastructure-as-code: resources, roles, security policies, networking. Continuous deployment is enabled by Github Actions. Onboarded bots make use of a reusable workflow that lets developers focus on designing bot functionality rather than stress over deployment and integration issues. We currently support `sandbox` deployment but can switch to `production` mode when ready.

## How to onboard a new bot

1. Get the following information from developer:
    * BOT_GITHUB_ORG_NAME
    * BOT_NAME (must be unique)
2. Add these into `shared/terraform/main.tf`
```hcl
module "bot_platform" {
    ...
    bot_configs = {
        "test-bot" = {
        github_org = "tee-gee-bots"
        }
        # "BOT_NAME" = {
        #   github_org = "BOT_GITHUB_ORG_NAME"
        # }
    }
}
```
3. Commit the change to deploy the new infrastructure

## Progress

### Current implementation
* Easy to onboard multiple bot developers using `tee-gee-bots/test-bot` as template repo. The how-to checklists in `README.md` has been tested for new repos created both in-/out-side organization
* Created a couple of new test bots for testing:
    * Bot 1: Produces input messages on demand (e.g. Present real-user members with `Would you like to... Y/N` question)
    * Bot 2: Monitors real-user replies to input message
        * Bot reply content is contingent on `Y`/`N`
        * Reply gets stored into redis backend
        * Old replies are indexed by response state (Y/N) and can be `/fetched`

### Todo
* API server (backend) improvements:
    * Add Postgresql client manager between redis backend and api-server. Want to make db searchable, want to better visualize content of stored messages/indexes
    * Come up with better data schema/api routes that support Postgresql querying - update existing bots and bot template.
    * Cloudfrong logging for api-server too
    * CORS for frontend website - how to do it if using widget? Something about api tokens in header... (need to study)
    * Rate limit requests from clients (from bots and from front-end)
    * Data retention policy, ensure anonymization
    * Reduce infrastructure cost, scalable?
    * Transition to maintain parallel Sandbox vs Prodction environments
* Implement visualization (frontend): **End to end goal** of the project is for Bot/human interaction to be visible on some fronten. Maybe bots should present users with a link to a frontend website/tweet that shows their impact
    * Rewrite sandbox-website in React to poll api-server for updated input, or
    * A widget is even better for distribution - can be plugged in to existing websites
    * A tweet might be more interesting
    * More run if we display different content types based on api-server response. For example, show images from an image bank stored on separate s3 instance, or a dashboard of some sort. Need more creative input
* Bot bugs:
    * Wishengine bot reply gets cut off on comma/punctuation
