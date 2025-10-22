# Backends API

fscheduler 提供多种队列后端实现，支持不同的使用场景。

## QueueBackend (抽象基类)

::: fscheduler.backends.base.QueueBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## MemoryBackend

::: fscheduler.backends.memory.MemoryBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## SQLiteBackend

::: fscheduler.backends.sqlite_backend.SQLiteBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## RedisBackend

::: fscheduler.backends.redis_backend.RedisBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## RabbitMQBackend

::: fscheduler.backends.rabbitmq_backend.RabbitMQBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google
