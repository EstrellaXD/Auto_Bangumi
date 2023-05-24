import Axios from 'axios';

const { auth } = useAuth();

export const axios = Axios.create({
  headers: {
    Authorization: auth.value,
  },
});
