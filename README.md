
# API WEB HOSPITAL-SDLG

This is te backend web of the hospital-sdlg


## Feactures

- [SPA Manager](https://github.com/Joaquin-Gael/hospital_back/tree/main/app)
- [Test README](https://github.com/Joaquin-Gael/hospital_back/tree/main/test)
- [Local Storage](https://github.com/Joaquin-Gael/hospital_back/tree/main/app/storage)


## API Reference

#### Redirect to frontend

```http
  GET /
```

| Parameter | Type     | Description                |
| :-------- | :------- | :------------------------- |
| `None` | `None` | Not need token |

#### Get item

```http
  GET /{token}/api/{path}
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `string` | **Required**. token to fetch |



## Authors

- [@Joaquin-Gael](https://www.github.com/Joaquin-Gael)


## Badges

<p align="left">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=python,fastapi,postgresql,neon" />
  </a>
</p>

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![GPLv3 License](https://img.shields.io/badge/License-GPL%20v3-yellow.svg)](https://opensource.org/licenses/)
[![AGPL License](https://img.shields.io/badge/license-AGPL-blue.svg)](http://www.gnu.org/licenses/agpl-3.0)