export type Auth = {
  access_token: string;
  token_type: string;
  expire: number;
};

export type Logout = {
  message: 'logout success';
};

export type Update = {
  message: 'update success';
};
