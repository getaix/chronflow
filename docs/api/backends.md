# Backends API

chronflow 提供多种队列后端实现，支持不同的使用场景。

## QueueBackend (抽象基类)

::: chronflow.backends.base.QueueBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## MemoryBackend

::: chronflow.backends.memory.MemoryBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## SQLiteBackend

::: chronflow.backends.sqlite_backend.SQLiteBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## RedisBackend

::: chronflow.backends.redis_backend.RedisBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google

## RabbitMQBackend

::: chronflow.backends.rabbitmq_backend.RabbitMQBackend
    options:
      show_source: false
      heading_level: 3
      merge_init_into_class: true
      docstring_style: google
