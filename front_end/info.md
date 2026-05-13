docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=123456 \
  -v mongodb_data:/data/db \
  --restart=always \
  docker.m.daocloud.io/library/mongo:latest