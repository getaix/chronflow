# Backends API {#zh-backends-api}

Symphra Scheduler 提供多种队列后端实现，支持不同的使用场景。

## QueueBackend (抽象基类) {#zh-backends-queuebackend}

::: symphra_scheduler.backends.base.QueueBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## MemoryBackend {#zh-backends-memorybackend}

::: symphra_scheduler.backends.memory.MemoryBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## SQLiteBackend {#zh-backends-sqlitebackend}

::: symphra_scheduler.backends.sqlite_backend.SQLiteBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## RedisBackend {#zh-backends-redisbackend}

::: symphra_scheduler.backends.redis_backend.RedisBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## RabbitMQBackend {#zh-backends-rabbitmqbackend}

::: symphra_scheduler.backends.rabbitmq_backend.RabbitMQBackend
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google