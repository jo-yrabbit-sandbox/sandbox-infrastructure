## API server

An api-server with backend redis database which:
* Stores messages from multiple bots
* Allows website to get stored messages

```sh
Bot 1 ---> \
Bot 2 ---> API Server (EC2) ---> Redis (ElastiCache)
Bot 3 ---> /     ^
                 |
            Website (S3)
```

### WIP